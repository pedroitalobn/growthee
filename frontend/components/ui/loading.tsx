'use client'

import { cn } from '@/lib/utils'

interface LoadingProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
  text?: string
}

export function Loading({ size = 'md', className, text }: LoadingProps) {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12'
  }

  return (
    <div className={cn('loading-container p-4', className)}>
      <div className="flex flex-col items-center justify-center space-y-4">
        <div
          className={cn(
            'smooth-spin rounded-full border-2 border-muted border-t-primary transition-all duration-300 ease-out',
            sizeClasses[size]
          )}
        />
        {text && (
          <p className="text-sm text-muted-foreground smooth-fade transition-opacity duration-500 ease-out">{text}</p>
        )}
      </div>
    </div>
  )
}

export function LoadingPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-8">
      <Loading size="lg" text="Carregando..." className="p-8" />
    </div>
  )
}

export function LoadingSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn('loading-skeleton bg-muted rounded transition-all duration-1000 ease-out', className)} />
  )
}

// Enhanced skeleton components for better UX
export function CardSkeleton() {
  return (
    <div className="border rounded-lg p-6 space-y-4 bg-white dark:bg-gray-800">
      <div className="flex items-center space-x-3">
        <LoadingSkeleton className="h-10 w-10 rounded-full" />
        <div className="space-y-2 flex-1">
          <LoadingSkeleton className="h-4 w-3/4" />
          <LoadingSkeleton className="h-3 w-1/2" />
        </div>
      </div>
      <LoadingSkeleton className="h-20 w-full rounded-md" />
      <div className="flex space-x-2">
        <LoadingSkeleton className="h-8 w-20 rounded" />
        <LoadingSkeleton className="h-8 w-16 rounded" />
      </div>
    </div>
  )
}

// API Keys skeleton
export function ApiKeysSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <LoadingSkeleton className="h-6 w-32" />
          <LoadingSkeleton className="h-4 w-64" />
        </div>
        <LoadingSkeleton className="h-10 w-24 rounded" />
      </div>
      <div className="space-y-3">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="border rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <LoadingSkeleton className="h-8 w-8 rounded" />
                <div className="space-y-1">
                  <LoadingSkeleton className="h-4 w-24" />
                  <LoadingSkeleton className="h-3 w-32" />
                </div>
              </div>
              <div className="flex space-x-2">
                <LoadingSkeleton className="h-8 w-8 rounded" />
                <LoadingSkeleton className="h-8 w-8 rounded" />
              </div>
            </div>
            <LoadingSkeleton className="h-10 w-full rounded" />
            <div className="flex justify-between text-sm">
              <LoadingSkeleton className="h-3 w-20" />
              <LoadingSkeleton className="h-3 w-16" />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// Dashboard stats skeleton
export function DashboardStatsSkeleton() {
  return (
    <div className="flex-1 space-y-4 p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <LoadingSkeleton className="h-9 w-32" />
      </div>
      <div className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="border rounded-lg p-6 space-y-3">
              <div className="flex items-center justify-between">
                <LoadingSkeleton className="h-4 w-20" />
                <LoadingSkeleton className="h-5 w-5 rounded" />
              </div>
              <LoadingSkeleton className="h-8 w-16" />
              <LoadingSkeleton className="h-3 w-24" />
            </div>
          ))}
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <LoadingSkeleton className="h-64 rounded-lg" />
          <LoadingSkeleton className="h-64 rounded-lg" />
        </div>
      </div>
    </div>
  )
}

// Credits history skeleton
export function CreditsHistorySkeleton() {
  return (
    <div className="space-y-6">
      {/* Stats cards */}
      <div className="grid gap-4 md:grid-cols-3">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="border rounded-lg p-4 space-y-2">
            <LoadingSkeleton className="h-4 w-24" />
            <LoadingSkeleton className="h-6 w-16" />
            <LoadingSkeleton className="h-3 w-20" />
          </div>
        ))}
      </div>
      
      {/* Chart area */}
      <div className="border rounded-lg p-6">
        <LoadingSkeleton className="h-4 w-32 mb-4" />
        <LoadingSkeleton className="h-64 w-full rounded" />
      </div>
      
      {/* History table */}
      <div className="border rounded-lg">
        <div className="p-4 border-b">
          <LoadingSkeleton className="h-5 w-40" />
        </div>
        <div className="divide-y">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="p-4 flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <LoadingSkeleton className="h-8 w-8 rounded" />
                <div className="space-y-1">
                  <LoadingSkeleton className="h-4 w-32" />
                  <LoadingSkeleton className="h-3 w-24" />
                </div>
              </div>
              <div className="text-right space-y-1">
                <LoadingSkeleton className="h-4 w-16" />
                <LoadingSkeleton className="h-3 w-12" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// API Documentation skeleton
export function ApiDocumentationSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-2">
        <LoadingSkeleton className="h-6 w-6 rounded" />
        <LoadingSkeleton className="h-7 w-48" />
      </div>
      
      <div className="space-y-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="border rounded-lg">
            <div className="p-4 border-b">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <LoadingSkeleton className="h-6 w-16 rounded" />
                  <LoadingSkeleton className="h-5 w-32" />
                </div>
                <LoadingSkeleton className="h-4 w-4 rounded" />
              </div>
              <LoadingSkeleton className="h-4 w-3/4 mt-2" />
            </div>
            <div className="p-4 space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <LoadingSkeleton className="h-4 w-20" />
                  <LoadingSkeleton className="h-32 w-full rounded" />
                </div>
                <div className="space-y-2">
                  <LoadingSkeleton className="h-4 w-24" />
                  <LoadingSkeleton className="h-32 w-full rounded" />
                </div>
              </div>
              <div className="flex space-x-2">
                <LoadingSkeleton className="h-9 w-20 rounded" />
                <LoadingSkeleton className="h-9 w-16 rounded" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// Table skeleton for generic tables
export function TableSkeleton({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="border rounded-lg">
      <div className="border-b p-4">
        <div className="flex space-x-4">
          {[...Array(cols)].map((_, i) => (
            <LoadingSkeleton key={i} className="h-4 w-20" />
          ))}
        </div>
      </div>
      <div className="divide-y">
        {[...Array(rows)].map((_, i) => (
          <div key={i} className="p-4">
            <div className="flex space-x-4">
              {[...Array(cols)].map((_, j) => (
                <LoadingSkeleton key={j} className="h-4 w-20" />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export function UserProfileSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <LoadingSkeleton className="h-6 w-6 rounded" />
        <LoadingSkeleton className="h-8 w-48" />
      </div>
      
      <div className="grid gap-6 md:grid-cols-2">
        <div className="border rounded-lg p-6">
          <div className="space-y-2 mb-4">
            <LoadingSkeleton className="h-6 w-32" />
            <LoadingSkeleton className="h-4 w-48" />
          </div>
          <div className="space-y-4">
            <div className="space-y-2">
              <LoadingSkeleton className="h-4 w-16" />
              <LoadingSkeleton className="h-10 w-full rounded" />
            </div>
            <div className="space-y-2">
              <LoadingSkeleton className="h-4 w-20" />
              <LoadingSkeleton className="h-10 w-full rounded" />
            </div>
            <div className="space-y-2">
              <LoadingSkeleton className="h-4 w-24" />
              <LoadingSkeleton className="h-10 w-full rounded" />
            </div>
            <LoadingSkeleton className="h-9 w-20 rounded" />
          </div>
        </div>
        
        <div className="border rounded-lg p-6">
          <div className="space-y-2 mb-4">
            <LoadingSkeleton className="h-6 w-40" />
            <LoadingSkeleton className="h-4 w-56" />
          </div>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <LoadingSkeleton className="h-4 w-16" />
              <LoadingSkeleton className="h-6 w-16 rounded" />
            </div>
            <div className="flex items-center justify-between">
              <LoadingSkeleton className="h-4 w-20" />
              <LoadingSkeleton className="h-6 w-20 rounded" />
            </div>
            <div className="flex items-center justify-between">
              <LoadingSkeleton className="h-4 w-24" />
              <LoadingSkeleton className="h-6 w-24 rounded" />
            </div>
          </div>
        </div>
      </div>
      
      <div className="grid gap-6 md:grid-cols-3">
        <div className="border rounded-lg p-6">
          <div className="space-y-2 mb-4">
            <LoadingSkeleton className="h-6 w-28" />
          </div>
          <LoadingSkeleton className="h-8 w-16" />
          <LoadingSkeleton className="h-4 w-32 mt-2" />
        </div>
        
        <div className="border rounded-lg p-6">
          <div className="space-y-2 mb-4">
            <LoadingSkeleton className="h-6 w-32" />
          </div>
          <LoadingSkeleton className="h-8 w-20" />
          <LoadingSkeleton className="h-4 w-36 mt-2" />
        </div>
        
        <div className="border rounded-lg p-6">
          <div className="space-y-2 mb-4">
            <LoadingSkeleton className="h-6 w-24" />
          </div>
          <LoadingSkeleton className="h-8 w-12" />
          <LoadingSkeleton className="h-4 w-28 mt-2" />
        </div>
      </div>
    </div>
  )
}