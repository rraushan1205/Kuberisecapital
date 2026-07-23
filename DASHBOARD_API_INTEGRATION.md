# Dashboard API Integration Guide

This document describes how to integrate the mockup dashboard with real API endpoints.

## Current Status

The dashboard is currently running with **mock data** to demonstrate the UI and user experience. All data is simulated and updates are animated for demonstration purposes.

## Switching to Real API

To connect the dashboard to real backend APIs, follow these steps:

### 1. Toggle Mock Data Off

In `src/features/dashboard/lib/mock-data.ts`, change:

```typescript
export const USE_MOCK_DATA = true;
```

to:

```typescript
export const USE_MOCK_DATA = false;
```

### 2. Required API Endpoints

Implement the following endpoints in your backend:

#### Dashboard Snapshot
```
GET /api/v1/client/dashboard
```

**Response Type:** `DashboardSnapshot`

```json
{
  "profile": {
    "name": "User Name",
    "subscriptionStatus": "Pro · Active",
    "connectedBroker": "Zerodha - Live"
  },
  "strategy": {
    "status": "Running",
    "selectedName": "Momentum Breakout",
    "scriptFileName": "momentum_breakout_v3.py"
  },
  "pnl": {
    "daily": "₹4,285.50",
    "overall": "₹1,18,940.75"
  },
  "positions": {
    "open": 3,
    "closed": 27
  },
  "subscription": {
    "status": "Pro · renews 15 Aug 2026"
  },
  "broker": {
    "provider": "Zerodha Kite",
    "status": "ID A84521"
  },
  "preferences": {
    "lotSize": "2 lots · NIFTY",
    "riskSettings": "Max loss ₹5,000/day · 5 pos. cap"
  }
}
```

#### Positions Data
```
GET /api/v1/client/positions
```

**Response Type:**

```json
{
  "open": [
    {
      "id": "1",
      "symbol": "NIFTY 24800 CE",
      "type": "LONG",
      "quantity": 50,
      "entryPrice": 142.30,
      "currentPrice": 156.45,
      "pnl": 707.50,
      "pnlPercent": 9.94,
      "status": "open"
    }
  ],
  "closed": [
    {
      "id": "4",
      "symbol": "NIFTY 24700 PE",
      "type": "SHORT",
      "quantity": 50,
      "entryPrice": 128.50,
      "currentPrice": 95.30,
      "pnl": 1660.00,
      "pnlPercent": 25.84,
      "status": "closed"
    }
  ]
}
```

#### Execution Logs
```
GET /api/v1/client/executions
```

**Response Type:** Array of `ExecutionLog`

```json
[
  {
    "id": "1",
    "timestamp": "10:42 AM",
    "type": "ORDER",
    "message": "BOUGHT 1 lot NIFTY 24800 CE @ ₹142.30",
    "status": "Filled",
    "details": "Order ID: 240722001234 · Executed at NSE"
  }
]
```

**Log Types:** `ORDER`, `SIGNAL`, `SYSTEM`, `ERROR`
**Status Values:** `Filled`, `Executed`, `Info`, `Warning`, `Failed`

#### P&L Chart Data
```
GET /api/v1/client/pnl/history
```

**Response Type:**

```json
{
  "daily": [
    { "time": "09:15", "value": 0 },
    { "time": "09:30", "value": 450 },
    { "time": "10:00", "value": 1240 }
  ],
  "overall": [
    { "date": "Feb 2026", "value": 0 },
    { "date": "Mar", "value": 22450 },
    { "date": "Apr", "value": 48920 }
  ]
}
```

#### Marketplace Strategies
```
GET /api/v1/client/marketplace/strategies
```

**Response Type:** Array of `MarketplaceStrategy`

```json
[
  {
    "id": "momentum-breakout",
    "name": "Momentum Breakout",
    "status": "Active",
    "scriptFileName": "momentum_breakout_v3.py"
  }
]
```

### 3. Update API Client

The hooks in `src/features/dashboard/hooks/use-dashboard-data.ts` already have placeholders for real API calls. Uncomment and implement them:

```typescript
export function usePositions() {
  return useQuery({
    queryKey: ["dashboard", "positions"],
    queryFn: USE_MOCK_DATA
      ? () => simulateApiDelay({ open: MOCK_OPEN_POSITIONS, closed: MOCK_CLOSED_POSITIONS })
      : async () => {
          // Implement your API call here
          const response = await fetch('/api/v1/client/positions', {
            credentials: 'include',
            headers: { 'Accept': 'application/json' }
          });
          if (!response.ok) throw new Error('Failed to fetch positions');
          return response.json();
        }
  });
}
```

### 4. Authentication

All API endpoints should:
- Accept session cookies (`credentials: 'include'`)
- Return 401 for unauthorized requests
- Support CORS if frontend and backend are on different domains

### 5. Real-time Updates

For live market data and position updates, consider:

1. **WebSocket Connection** for real-time price updates
2. **Polling** with React Query's `refetchInterval` option
3. **Server-Sent Events (SSE)** for one-way updates

Example with polling:

```typescript
export function useDashboardSnapshot() {
  return useQuery({ 
    queryKey: ["dashboard", "snapshot"], 
    queryFn: getDashboardSnapshot,
    refetchInterval: 5000, // Refetch every 5 seconds
    refetchIntervalInBackground: true
  });
}
```

### 6. Error Handling

The dashboard already handles loading and error states. Ensure your API returns appropriate error responses:

```json
{
  "error": "Unauthorized",
  "message": "Session expired. Please login again.",
  "code": 401
}
```

## Market Ticker

The market ticker in `src/features/dashboard/components/market-ticker.tsx` currently uses mock data. To connect to real market data:

1. Create an endpoint: `GET /api/v1/market/ticker`
2. Return an array of current market prices
3. Use WebSocket or polling for updates
4. Update the component to fetch from your API

## CDN Integration for Static Assets

If you need to serve static assets (strategy files, reports, etc.) from a CDN:

1. Configure CDN URL in environment variables:
   ```
   NEXT_PUBLIC_CDN_BASE_URL=https://cdn.yourapp.com
   ```

2. Create a helper function:
   ```typescript
   export function getCdnUrl(path: string) {
     const cdnBase = process.env.NEXT_PUBLIC_CDN_BASE_URL || '';
     return `${cdnBase}${path}`;
   }
   ```

3. Use it for file downloads:
   ```typescript
   <a href={getCdnUrl('/strategies/momentum_breakout_v3.py')}>
     Download Strategy
   </a>
   ```

## Testing Checklist

Before going live with real APIs:

- [ ] Test all API endpoints with real data
- [ ] Verify authentication and session management
- [ ] Test error states (network failures, 401s, 500s)
- [ ] Check loading states and transitions
- [ ] Verify data refresh intervals
- [ ] Test with various data volumes (empty, small, large datasets)
- [ ] Validate WebSocket connections (if using)
- [ ] Test on different networks (slow 3G, fast WiFi)
- [ ] Verify CORS configuration
- [ ] Test logout and session expiry flows

## Performance Optimization

Once connected to real APIs:

1. **Enable React Query DevTools** in development to monitor queries
2. **Configure stale times** to reduce unnecessary refetches
3. **Use optimistic updates** for immediate UI feedback
4. **Implement pagination** for large datasets (execution logs, positions)
5. **Add request caching** where appropriate

## Support

For questions or issues with API integration:
- Check the backend API documentation
- Review React Query documentation: https://tanstack.com/query/latest
- Check browser console for network errors
- Use the Network tab in DevTools to inspect API calls
