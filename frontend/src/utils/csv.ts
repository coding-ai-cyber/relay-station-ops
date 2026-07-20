type CsvColumn<T> = {
  title: string;
  value: keyof T | ((row: T) => unknown);
};

function csvCell(value: unknown): string {
  if (value === null || value === undefined) {
    return "";
  }
  const text = String(value);
  if (/[",\r\n]/.test(text)) {
    return `"${text.replaceAll('"', '""')}"`;
  }
  return text;
}

export function exportCsv<T>(filename: string, rows: T[], columns: CsvColumn<T>[]) {
  const header = columns.map((column) => csvCell(column.title)).join(",");
  const body = rows.map((row) =>
    columns
      .map((column) => {
        const value = typeof column.value === "function" ? column.value(row) : row[column.value];
        return csvCell(value);
      })
      .join(",")
  );

  const blob = new Blob([`\uFEFF${[header, ...body].join("\r\n")}`], {
    type: "text/csv;charset=utf-8"
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
