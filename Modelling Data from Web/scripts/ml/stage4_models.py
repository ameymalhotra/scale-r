"""Stage 4: Bayesian multiscale models of sited resilience investment (NumPyro, NUTS).

Library used by stage4_run.py. Model equations are in reports/ml/stage4_bayesian_report.md.

Scales
  county        the model intercept (one county, so it cannot be a level; county
                projects are not in the sited outcome anyway)
  city          u_j: jurisdiction random intercept (33 jurisdictions; Unincorporated
                Miami-Dade is one jurisdiction)
  neighbourhood structured part of the BYM2 effect (ICAR over the tract graph)
  tract         unstructured part of the BYM2 effect

BYM2 (Riebler et al. 2016): b_i = sigma * (sqrt(1 - rho) * theta_i + sqrt(rho / s) * phi_i),
theta ~ N(0, 1), phi ~ ICAR on the graph with a soft sum-to-zero constraint, s = the
scaling factor, rho = the share of b's variance that is spatially structured.
Priors: Normal(0, 1) on standardized coefficients; PC priors on the standard
deviations (exponential) and on rho (P(rho < 0.5) = 2/3, the INLA default).
"""
import os

os.environ.setdefault("XLA_FLAGS", "--xla_force_host_platform_device_count=4")
import json  # noqa: E402

import jax  # noqa: E402
import jax.numpy as jnp  # noqa: E402
import numpy as np  # noqa: E402
import numpyro  # noqa: E402
import numpyro.distributions as dist  # noqa: E402
import pandas as pd  # noqa: E402
from numpyro.infer import MCMC, NUTS, Predictive  # noqa: E402

import ml_common as C  # noqa: E402

numpyro.set_host_device_count(4)
jax.config.update("jax_enable_x64", True)
SEED = C.SEED
OUT = C.paths.OUT_ML / "stage4"
FITS = OUT / "fits"
HAZ = C.HAZ_MAIN
INTER = [f"{h}:vulnerability" for h in HAZ]


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------

def pc_sd_rate(upper, prob):
    """Exponential rate for a PC prior on a standard deviation: P(sigma > upper) = prob."""
    return -np.log(prob) / upper


def load_data():
    """The 697 training tracts in graph order, standardized design matrix, outcomes, graph."""
    t = C.load_table()
    tr = t[C.train_mask(t)].reset_index(drop=True)
    nodes = pd.read_csv(OUT / "graph_nodes.csv", dtype={"GEOID": str})
    assert (nodes.GEOID.values == tr.GEOID.values).all(), "graph order must match the training frame"
    edges = pd.read_csv(OUT / "graph_edges.csv")
    g = json.loads((OUT / "graph_summary.json").read_text())
    pca = pd.read_csv(C.paths.OUT_PCA / "pca_scores_tract.csv", dtype={"GEOID": str}).set_index("GEOID")
    rc1 = tr.GEOID.map(pca.RC1)
    if pd.Series(rc1.values).corr(tr.EP_POV150, method="spearman") < 0:
        rc1 = -rc1
    raw = tr[C.MAIN].copy()
    raw["vulnerability"] = rc1.values
    missing = raw.isna().sum()
    raw = raw.fillna(raw.median())             # one tract lacks 8 SVI values (D-099)
    sited_pr = (tr.sited_dollars / tr.population).to_numpy()
    return {"tr": tr, "raw": raw, "missing": missing[missing > 0].to_dict(), "edges": edges[["i", "j"]].to_numpy(),
            "scale": g["bym2_scaling_factor"], "y1": tr.T1.to_numpy().astype(int), "y2": sited_pr,
            "juris": pd.factorize(tr.jurisdiction)[0], "juris_names": list(pd.factorize(tr.jurisdiction)[1]),
            "folds": tr.fold_spatial.to_numpy()}


def design(raw, fit_rows):
    """Standardize with means and SDs from fit_rows only; add hazard x vulnerability interactions."""
    mu = raw.iloc[fit_rows].mean()
    sd = raw.iloc[fit_rows].std(ddof=0).replace(0, 1)
    Z = (raw - mu) / sd
    X = Z[C.MAIN].copy()
    for h, name in zip(HAZ, INTER):
        X[name] = Z[h] * Z["vulnerability"]
    return X, Z


def pc_rho_logpdf_fn(edges, n, scale, u=0.5, alpha=2 / 3):
    """PC prior on the BYM2 mixing parameter, from the eigenvalues of the scaled ICAR covariance."""
    W = np.zeros((n, n))
    W[edges[:, 0], edges[:, 1]] = 1
    W = W + W.T
    Q = np.diag(W.sum(1)) - W
    Qp = Q + np.eye(n) * Q.diagonal().max() * np.sqrt(np.finfo(float).eps)
    Qi = np.linalg.inv(Qp)
    one = np.ones((n, 1))
    Qi = Qi - Qi @ one @ np.linalg.inv(one.T @ Qi @ one) @ one.T @ Qi
    ev = np.linalg.eigvalsh(Qi / scale)
    ev = jnp.asarray(ev[ev > 1e-8])            # drop the constrained (null) direction

    def kld(rho):
        a = ev - 1.0
        return 0.5 * jnp.sum(rho * a - jnp.log1p(rho * a))

    def d(rho):
        return jnp.sqrt(2.0 * kld(rho))

    lam = np.log(1.0 / (1.0 - alpha)) / float(d(u))  # P(rho < u) = alpha

    def logpdf(rho):
        a = ev - 1.0
        dk = 0.5 * jnp.sum(rho * a * a / (1.0 + rho * a))
        dd = dk / jnp.maximum(d(rho), 1e-12)
        return jnp.log(lam) - lam * d(rho) + jnp.log(jnp.abs(dd) + 1e-30)

    return logpdf, lam


# --------------------------------------------------------------------------
# model pieces
# --------------------------------------------------------------------------

def icar_basis(edges, n):
    """B with phi = B z, z ~ N(0, I): an exact draw from the sum-to-zero ICAR. Used only for prior predictive checks."""
    W = np.zeros((n, n))
    W[edges[:, 0], edges[:, 1]] = 1
    W = W + W.T
    ev, V = np.linalg.eigh(np.diag(W.sum(1)) - W)
    keep = ev > 1e-8
    return jnp.asarray(V[:, keep] / np.sqrt(ev[keep]))


def icar(name, n, e0, e1, basis=None):
    if basis is not None:
        z = numpyro.sample(f"{name}_z", dist.Normal(0.0, 1.0).expand([basis.shape[1]]))
        return numpyro.deterministic(name, basis @ z)
    phi = numpyro.sample(name, dist.ImproperUniform(dist.constraints.real, (), (n,)))
    numpyro.factor(f"{name}_icar", -0.5 * jnp.sum((phi[e0] - phi[e1]) ** 2))
    numpyro.factor(f"{name}_sum0", dist.Normal(0.0, 0.001 * n).log_prob(jnp.sum(phi)))
    return phi


def bym2(name, n, e0, e1, scale, sd_rate, rho_logpdf, basis=None):
    sigma = numpyro.sample(f"sigma_{name}", dist.Exponential(sd_rate))
    rho = numpyro.sample(f"rho_{name}", dist.Uniform(0.0, 1.0))
    numpyro.factor(f"rho_{name}_pc", rho_logpdf(rho))
    theta = numpyro.sample(f"theta_{name}", dist.Normal(0.0, 1.0).expand([n]))
    phi = icar(f"phi_{name}", n, e0, e1, basis)
    structured = sigma * jnp.sqrt(rho / scale) * phi
    unstructured = sigma * jnp.sqrt(1.0 - rho) * theta
    numpyro.deterministic(f"bstruct_{name}", structured)
    numpyro.deterministic(f"bunstruct_{name}", unstructured)
    return structured + unstructured


def linear(X, n_j, juris, edges, scale, rho_logpdf, prior, use_juris, use_bym2, svc_cols=None, tag="1", basis=None):
    n, p = X.shape
    e0, e1 = edges[:, 0], edges[:, 1]
    alpha = numpyro.sample(f"alpha_{tag}", dist.Normal(prior["alpha_mu"], prior["alpha_sd"]))
    beta = numpyro.sample(f"beta_{tag}", dist.Normal(0.0, prior["beta_sd"]).expand([p]))
    eta = alpha + X @ beta
    if use_juris:
        su = numpyro.sample(f"sigma_juris_{tag}", dist.Exponential(prior["sd_rate"]))
        zu = numpyro.sample(f"z_juris_{tag}", dist.Normal(0.0, 1.0).expand([n_j]))
        u = numpyro.deterministic(f"u_juris_{tag}", su * zu)
        eta = eta + u[juris]
    if use_bym2 == "icar":
        # structured spatial effect only (D-101): used in Part 2, where a tract-level unstructured
        # effect cannot be told apart from the observation noise (one amount per tract)
        sg = numpyro.sample(f"sigma_sp_{tag}", dist.Exponential(prior["sd_rate"]))
        phi = icar(f"phi_sp_{tag}", n, e0, e1, basis)
        eta = eta + numpyro.deterministic(f"bstruct_sp_{tag}", sg * phi / jnp.sqrt(scale))
    elif use_bym2:
        eta = eta + bym2(f"sp_{tag}", n, e0, e1, scale, prior["sd_rate"], rho_logpdf, basis)
    if svc_cols is not None:
        for k, col in enumerate(svc_cols):
            sk = numpyro.sample(f"sigma_svc{k}_{tag}", dist.Exponential(prior["svc_rate"]))
            psi = icar(f"psi_svc{k}_{tag}", n, e0, e1, basis)
            dev = numpyro.deterministic(f"slope_dev{k}_{tag}", sk * psi / jnp.sqrt(scale))
            eta = eta + X[:, col] * dev
    return eta


def model_binary(X, y, obs_idx, n_j, juris, edges, scale, rho_logpdf, prior, use_juris=True, use_bym2=True,
                 svc_cols=None, basis=None):
    eta = linear(X, n_j, juris, edges, scale, rho_logpdf, prior, use_juris, use_bym2, svc_cols, "1", basis)
    numpyro.deterministic("eta", eta)
    numpyro.sample("y", dist.Bernoulli(logits=eta[obs_idx]), obs=None if y is None else y[obs_idx])


def model_amount(X, y, obs_idx, n_j, juris, edges, scale, rho_logpdf, prior, family="gamma", use_juris=True,
                 use_bym2="icar", basis=None):
    mu_log = linear(X, n_j, juris, edges, scale, rho_logpdf, prior, use_juris, use_bym2, None, "2", basis)
    numpyro.deterministic("mu_log", mu_log)
    m = mu_log[obs_idx]
    yy = None if y is None else y[obs_idx]
    if family == "gamma":
        k = numpyro.sample("shape", dist.Exponential(1.0))
        numpyro.sample("y", dist.Gamma(k, k / jnp.exp(m)), obs=yy)
    else:
        s = numpyro.sample("sigma_y", dist.HalfNormal(2.5))
        numpyro.sample("y", dist.LogNormal(m, s), obs=yy)


PRIORS = {
    # weakly informative (D-100); sd_rate: P(sd > 1) = 0.05 on the logit scale, P(sd > 2) = 0.05 on log dollars
    "binary": {"alpha_mu": 0.0, "alpha_sd": 2.5, "beta_sd": 1.0, "sd_rate": pc_sd_rate(1.0, 0.05),
               "svc_rate": pc_sd_rate(1.0, 0.05)},
    "binary_narrow": {"alpha_mu": 0.0, "alpha_sd": 2.5, "beta_sd": 0.5, "sd_rate": pc_sd_rate(0.5, 0.05),
                      "svc_rate": pc_sd_rate(0.5, 0.05)},
    "binary_wide": {"alpha_mu": 0.0, "alpha_sd": 2.5, "beta_sd": 2.5, "sd_rate": pc_sd_rate(2.0, 0.05),
                    "svc_rate": pc_sd_rate(2.0, 0.05)},
    "amount": {"alpha_mu": None, "alpha_sd": 2.5, "beta_sd": 1.0, "sd_rate": pc_sd_rate(2.0, 0.05)},
}


# --------------------------------------------------------------------------
# fitting
# --------------------------------------------------------------------------

def fit(model, kwargs, name, chains=4, warmup=1000, samples=1000, target_accept=0.95, seed=SEED, save=True,
        max_tree_depth=10, thinning=1):
    path = FITS / f"{name}.npz"
    if save and path.exists():
        z = np.load(path, allow_pickle=True)
        return {k: z[k] for k in z.files if k != "_meta"}, json.loads(str(z["_meta"]))
    FITS.mkdir(parents=True, exist_ok=True)
    kern = NUTS(model, target_accept_prob=target_accept, max_tree_depth=max_tree_depth)
    mcmc = MCMC(kern, num_warmup=warmup, num_samples=samples, num_chains=chains, chain_method="parallel",
                progress_bar=False, thinning=thinning)
    mcmc.run(jax.random.PRNGKey(seed), extra_fields=("diverging", "num_steps"), **kwargs)
    post = {k: np.asarray(v) for k, v in mcmc.get_samples(group_by_chain=True).items()}
    ex = mcmc.get_extra_fields(group_by_chain=True)
    meta = {"name": name, "chains": chains, "warmup": warmup, "samples": samples, "thinning": thinning, "target_accept": target_accept,
            "divergences": int(np.asarray(ex["diverging"]).sum()),
            "max_tree_depth_hits": int((np.asarray(ex["num_steps"]) >= 2 ** max_tree_depth - 1).sum())}
    # pointwise log likelihood of the observed sites, for LOO
    flat = {k: v.reshape((-1,) + v.shape[2:]) for k, v in post.items()}
    ll = numpyro.infer.util.log_likelihood(model, flat, **kwargs)["y"]
    post["loglik"] = np.asarray(ll).reshape(chains, samples // thinning, -1)
    if save:
        np.savez_compressed(path, **post, _meta=json.dumps(meta))
    return post, meta


def predictive(model, post, kwargs, seed=SEED):
    flat = {k: v.reshape((-1,) + v.shape[2:]) for k, v in post.items() if k not in ("loglik",)}
    return Predictive(model, posterior_samples=flat, return_sites=["y"])(jax.random.PRNGKey(seed + 1), **kwargs)


def prior_predictive(model, kwargs, n=1000, seed=SEED):
    return Predictive(model, num_samples=n, return_sites=["y"])(jax.random.PRNGKey(seed + 2), **kwargs)
