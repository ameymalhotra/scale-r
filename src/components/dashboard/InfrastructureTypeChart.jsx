import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';

/**
 * Isolated so recharts is not a static dependency of Dashboard (and therefore
 * of every route that imports Dashboard). The chart chunk downloads only when
 * this component actually renders on /dashboard.
 */
export default function InfrastructureTypeChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={180}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          outerRadius={55}
          fill="#8884d8"
          dataKey="value"
          isAnimationActive={false}
        >
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} stroke="#ffffff" strokeWidth={1} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value) => [`${value} projects`, 'Count']}
          contentStyle={{
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            border: '1px solid rgba(0, 0, 0, 0.1)',
            borderRadius: '8px',
            padding: '8px',
          }}
        />
        <Legend
          verticalAlign="bottom"
          height={36}
          iconType="circle"
          wrapperStyle={{ fontSize: '0.75em', paddingTop: '8px', color: '#445461' }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
