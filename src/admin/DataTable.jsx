import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table';
import { useVirtualizer } from '@tanstack/react-virtual';
import { FIELDS, formatFieldValue, isNewOption, parseFieldInput } from './fieldSchema.js';

const ROW_HEIGHT = 36;
const SELECT_WIDTH = 40;
const ACTIONS_WIDTH = 72;

function compareValues(a, b) {
  const aBlank = a == null || a === '';
  const bBlank = b == null || b === '';
  if (aBlank || bBlank) return aBlank === bBlank ? 0 : aBlank ? 1 : -1;
  if (typeof a === 'number' && typeof b === 'number') return a - b;
  return String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: 'base' });
}

const sortNullsLast = (rowA, rowB, columnId) => compareValues(rowA.getValue(columnId), rowB.getValue(columnId));

function includesText(row, columnId, filterValue) {
  const value = row.getValue(columnId);
  return String(value ?? '').toLowerCase().includes(String(filterValue).toLowerCase());
}

function equalsOption(row, columnId, filterValue) {
  if (filterValue === '__blank__') return row.getValue(columnId) == null || row.getValue(columnId) === '';
  return String(row.getValue(columnId) ?? '') === filterValue;
}

function searchAllFields(row, _columnId, filterValue) {
  const needle = String(filterValue).toLowerCase();
  return FIELDS.some((f) => String(row.original[f.key] ?? '').toLowerCase().includes(needle));
}

function CellEditor({ field, value, onCommit, onCancel, listId }) {
  const [text, setText] = useState(value == null ? '' : String(value));
  const ref = useRef(null);
  const finished = useRef(false);
  useEffect(() => {
    ref.current?.focus();
    ref.current?.select?.();
  }, []);

  const commit = () => {
    if (finished.current) return;
    finished.current = true;
    onCommit(parseFieldInput(field, text));
  };
  const onKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      commit();
    } else if (event.key === 'Escape') {
      event.preventDefault();
      finished.current = true;
      onCancel();
    }
  };

  return (
    <input
      ref={ref}
      className="admin-cell__input"
      aria-label={field.label}
      value={text}
      list={listId}
      inputMode={field.type === 'number' ? 'decimal' : undefined}
      onChange={(e) => setText(e.target.value)}
      onBlur={commit}
      onKeyDown={onKeyDown}
    />
  );
}

function DataCell({ row, field, state, editedFields, issues, onUpdate }) {
  const [editing, setEditing] = useState(false);
  const value = row[field.key];
  const error = issues?.errors?.[field.key];
  const warning = issues?.warnings?.[field.key];
  const edited = state === 'edited' && editedFields.includes(field.key);
  const readOnly = field.readOnly || state === 'deleted';

  const className = [
    'admin-cell',
    edited && 'is-edited',
    error && 'has-error',
    !error && warning && 'has-warning',
    field.type === 'number' && 'is-number',
  ]
    .filter(Boolean)
    .join(' ');

  if (editing) {
    return (
      <div className={className} role="gridcell">
        <CellEditor
          field={field}
          value={value}
          listId={field.options ? `admin-options-${field.key}` : undefined}
          onCommit={(next) => {
            setEditing(false);
            onUpdate(row.id, field.key, next);
          }}
          onCancel={() => setEditing(false)}
        />
      </div>
    );
  }

  const display = formatFieldValue(field, value);
  const title = error || warning || display;
  return (
    <div
      className={className}
      role="gridcell"
      tabIndex={readOnly ? -1 : 0}
      title={title}
      aria-readonly={readOnly || undefined}
      aria-invalid={error ? true : undefined}
      onClick={() => !readOnly && setEditing(true)}
      onKeyDown={(e) => {
        if (!readOnly && (e.key === 'Enter' || e.key === 'F2')) {
          e.preventDefault();
          setEditing(true);
        }
      }}
    >
      <span className="admin-cell__text">{display}</span>
      {isNewOption(field, value) && <span className="admin-badge">new</span>}
    </div>
  );
}

const STATE_LABEL = { new: 'New row', edited: 'Edited', deleted: 'Marked for deletion' };

export default function DataTable({
  rows,
  rowState,
  editedFields,
  validation,
  selectedIds,
  onToggleSelect,
  onToggleSelectAll,
  onUpdate,
  onOpenRow,
  globalFilter,
  onGlobalFilterChange,
  columnFilters,
  onColumnFiltersChange,
  sorting,
  onSortingChange,
}) {
  const scrollRef = useRef(null);

  const distinctValues = useMemo(() => {
    const map = {};
    for (const field of FIELDS) {
      if (!field.options) continue;
      const values = new Set(field.options);
      for (const r of rows) if (r[field.key] != null && r[field.key] !== '') values.add(String(r[field.key]));
      map[field.key] = [...values].sort((a, b) => a.localeCompare(b));
    }
    return map;
  }, [rows]);

  const columns = useMemo(
    () =>
      FIELDS.map((field) => ({
        id: field.key,
        accessorFn: (row) => row[field.key],
        header: field.label,
        size: field.width,
        sortingFn: sortNullsLast,
        filterFn: field.options ? equalsOption : includesText,
        meta: { field },
      })),
    [],
  );

  const table = useReactTable({
    data: rows,
    columns,
    state: { globalFilter, columnFilters, sorting },
    onGlobalFilterChange,
    onColumnFiltersChange,
    onSortingChange,
    globalFilterFn: searchAllFields,
    getRowId: (row) => String(row.id),
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  const tableRows = table.getRowModel().rows;
  const virtualizer = useVirtualizer({
    count: tableRows.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 12,
  });

  const gridTemplateColumns = [
    `${SELECT_WIDTH}px`,
    `${ACTIONS_WIDTH}px`,
    ...FIELDS.map((f) => `${f.width}px`),
  ].join(' ');
  const totalWidth = SELECT_WIDTH + ACTIONS_WIDTH + FIELDS.reduce((sum, f) => sum + f.width, 0);

  const visibleIds = tableRows.map((r) => r.original.id);
  const allVisibleSelected = visibleIds.length > 0 && visibleIds.every((id) => selectedIds.has(id));

  return (
    <div className="admin-grid-wrap">
      {FIELDS.filter((f) => f.options).map((f) => (
        <datalist key={f.key} id={`admin-options-${f.key}`}>
          {distinctValues[f.key].map((v) => (
            <option key={v} value={v} />
          ))}
        </datalist>
      ))}

      <div
        ref={scrollRef}
        className="admin-grid"
        role="grid"
        aria-rowcount={tableRows.length + 1}
        aria-colcount={FIELDS.length + 2}
        aria-label="Project data (draft)"
      >
        <div className="admin-grid__head" style={{ width: totalWidth }} role="rowgroup">
          <div className="admin-grid__row admin-grid__row--head" style={{ gridTemplateColumns }} role="row">
            <div className="admin-cell admin-cell--head" role="columnheader">
              <input
                type="checkbox"
                aria-label="Select all visible rows"
                checked={allVisibleSelected}
                onChange={() => onToggleSelectAll(visibleIds, !allVisibleSelected)}
              />
            </div>
            <div className="admin-cell admin-cell--head" role="columnheader">
              <span className="sr-only">Row actions</span>
            </div>
            {table.getHeaderGroups()[0].headers.map((header) => {
              const sorted = header.column.getIsSorted();
              return (
                <div
                  key={header.id}
                  className="admin-cell admin-cell--head"
                  role="columnheader"
                  aria-sort={sorted === 'asc' ? 'ascending' : sorted === 'desc' ? 'descending' : 'none'}
                >
                  <button type="button" className="admin-sort" onClick={header.column.getToggleSortingHandler()}>
                    {flexRender(header.column.columnDef.header, header.getContext())}
                    <span aria-hidden="true">{sorted === 'asc' ? ' ▲' : sorted === 'desc' ? ' ▼' : ''}</span>
                  </button>
                </div>
              );
            })}
          </div>
          <div className="admin-grid__row admin-grid__row--filters" style={{ gridTemplateColumns }} role="row">
            <div className="admin-cell admin-cell--head" role="columnheader" />
            <div className="admin-cell admin-cell--head" role="columnheader" />
            {table.getHeaderGroups()[0].headers.map((header) => {
              const { field } = header.column.columnDef.meta;
              const value = header.column.getFilterValue() ?? '';
              return (
                <div key={header.id} className="admin-cell admin-cell--head" role="columnheader">
                  {field.options ? (
                    <select
                      className="admin-filter"
                      aria-label={`Filter ${field.label}`}
                      value={value}
                      onChange={(e) => header.column.setFilterValue(e.target.value || undefined)}
                    >
                      <option value="">All</option>
                      <option value="__blank__">(blank)</option>
                      {distinctValues[field.key].map((v) => (
                        <option key={v} value={v}>
                          {v}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      className="admin-filter"
                      aria-label={`Filter ${field.label}`}
                      placeholder="Filter…"
                      value={value}
                      onChange={(e) => header.column.setFilterValue(e.target.value || undefined)}
                    />
                  )}
                </div>
              );
            })}
          </div>
        </div>

        <div
          className="admin-grid__body"
          style={{ height: virtualizer.getTotalSize(), width: totalWidth }}
          role="rowgroup"
        >
          {virtualizer.getVirtualItems().map((item) => {
            const row = tableRows[item.index].original;
            const state = rowState(row.id);
            const issues = validation.byId.get(row.id);
            const hasError = issues && Object.keys(issues.errors).length > 0;
            const fieldsEdited = editedFields(row.id);
            return (
              <div
                key={row.id}
                className={[
                  'admin-grid__row',
                  state && `is-${state}`,
                  hasError && 'has-error',
                  selectedIds.has(row.id) && 'is-selected',
                ]
                  .filter(Boolean)
                  .join(' ')}
                style={{ gridTemplateColumns, transform: `translateY(${item.start}px)`, height: ROW_HEIGHT }}
                role="row"
                aria-rowindex={item.index + 2}
              >
                <div className="admin-cell" role="gridcell">
                  <input
                    type="checkbox"
                    aria-label={`Select ${row.project_na || row.implementa || 'row'}`}
                    checked={selectedIds.has(row.id)}
                    onChange={() => onToggleSelect(row.id)}
                  />
                </div>
                <div className="admin-cell admin-cell--actions" role="gridcell">
                  <span
                    className={`admin-dot${state ? ` admin-dot--${state}` : ''}${hasError ? ' admin-dot--error' : ''}`}
                    title={hasError ? 'Has errors' : STATE_LABEL[state] || 'Unchanged'}
                  />
                  <button
                    type="button"
                    className="admin-btn admin-btn--tiny"
                    onClick={() => onOpenRow(row.id)}
                    aria-label={`Open ${row.project_na || row.implementa || 'row'} in the row editor`}
                  >
                    Open
                  </button>
                </div>
                {FIELDS.map((field) => (
                  <DataCell
                    key={field.key}
                    row={row}
                    field={field}
                    state={state}
                    editedFields={fieldsEdited}
                    issues={issues}
                    onUpdate={onUpdate}
                  />
                ))}
              </div>
            );
          })}
        </div>
        {tableRows.length === 0 && <p className="admin-empty">No rows match the current search and filters.</p>}
      </div>
      <p className="admin-muted admin-grid__count">
        Showing {tableRows.length.toLocaleString()} of {rows.length.toLocaleString()} rows
      </p>
    </div>
  );
}
