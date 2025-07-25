import * as React from "react"
import { cn } from "@/lib/utils"

interface DataTableProps extends React.HTMLAttributes<HTMLDivElement> {
  data?: any[]
  columns?: any[]
}

const DataTable = React.forwardRef<HTMLDivElement, DataTableProps>(
  ({ className, data = [], columns = [], ...props }, ref) => (
    <div
      ref={ref}
      className={cn("w-full", className)}
      {...props}
    >
      <div className="rounded-md border">
        <table className="w-full">
          <thead>
            <tr className="border-b">
              {columns.map((column, index) => (
                <th key={index} className="h-12 px-4 text-left align-middle font-medium">
                  {column.header || column.key}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, rowIndex) => (
              <tr key={rowIndex} className="border-b">
                {columns.map((column, colIndex) => (
                  <td key={colIndex} className="p-4 align-middle">
                    {row[column.key] || '-'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
)
DataTable.displayName = "DataTable"

export { DataTable }