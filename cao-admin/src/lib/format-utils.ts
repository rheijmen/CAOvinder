/**
 * Utility functions for consistent formatting across the application
 */

/**
 * Format a date consistently to avoid SSR hydration mismatches
 * @param date - The date to format (string, Date, or null/undefined)
 * @returns Formatted date string or "-" for null/undefined
 */
export function formatDate(date: string | Date | null | undefined): string {
  if (!date) return "-";

  try {
    const dateObj = typeof date === 'string' ? new Date(date) : date;

    // Check if valid date
    if (isNaN(dateObj.getTime())) return "-";

    // Use consistent format to avoid hydration mismatches
    // Format: MM/DD/YYYY
    return dateObj.toLocaleDateString('en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      timeZone: 'UTC' // Use UTC to ensure consistency between server and client
    });
  } catch (error) {
    console.error('Error formatting date:', error);
    return "-";
  }
}

/**
 * Format a date and time consistently
 * @param date - The date to format
 * @returns Formatted date and time string
 */
export function formatDateTime(date: string | Date | null | undefined): string {
  if (!date) return "-";

  try {
    const dateObj = typeof date === 'string' ? new Date(date) : date;

    if (isNaN(dateObj.getTime())) return "-";

    // Use fixed format to prevent hydration errors
    // Format: MM/DD/YYYY, HH:MM:SS (24-hour format)
    return dateObj.toLocaleDateString('en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false, // Use 24-hour format for consistency
      timeZone: 'UTC'
    });
  } catch (error) {
    console.error('Error formatting datetime:', error);
    return "-";
  }
}

/**
 * Format a number with consistent thousands separators
 * @param num - The number to format
 * @returns Formatted number string
 */
export function formatNumber(num: number | null | undefined): string {
  if (num == null) return "0";

  // Use fixed locale for consistency to prevent hydration errors
  return num.toLocaleString('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  });
}

/**
 * Format file size in human-readable format
 * @param bytes - File size in bytes
 * @returns Formatted file size string
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';

  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

/**
 * Format a number as currency
 * @param amount - The amount to format
 * @param currency - Currency code (default: EUR)
 * @returns Formatted currency string
 */
export function formatCurrency(amount: number, currency: string = 'EUR'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(amount);
}