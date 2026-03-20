

# NSE Pre-Open Scanner Dashboard

A professional, real-time stock market pre-open scanner with a Bloomberg Terminal-inspired dark theme, WebSocket live data feed, and comprehensive filtering/sorting controls.

---

## Page 1: Login Page (`/`)
- Full-screen centered card on a dark gradient background (#0a0e27 → #1a1f3a)
- "NSE Pre-Open Scanner" branding at top
- Username and password fields with a cyan full-width login button
- Loading spinner on submit, red error messages on failure
- On success: stores JWT token and redirects to dashboard
- API: `POST /api/login` to `localhost:8000`

## Page 2: Dashboard (`/dashboard`) — Protected Route
Redirects to login if no token is present.

### Header (sticky)
- Logo text in cyan on the left
- Live IST clock updating every second in the center
- WebSocket connection status (green/red dot) and logout button on the right

### Stats Cards Row (4 cards)
- **Total Stocks** — count of all stocks
- **Gainers** — stocks with positive change % (green)
- **Losers** — stocks with negative change % (red)
- **Last Update** — timestamp of most recent data

### Controls Bar
- **Sort by** dropdown: Change %, Volume, Price
- **Order** toggle: Desc (default) / Asc
- **Show** dropdown: Top 10, 25, 50 (default), All
- **Search** input to filter by symbol (debounced 300ms)
- **Auto-refresh** toggle (ON by default, cyan indicator)

### Data Table
- Columns: Rank, Symbol, LTP (₹), Change (₹), Change %, Volume, Buy Qty, Sell Qty, Last Update
- Color-coded values (green for gains, red for losses)
- Highlighted rows for stocks with ≥2% change
- Alternating row colors, hover highlights
- Skeleton loading state, empty/no-match states
- Indian number formatting (K, Cr suffixes)

### Footer
- "Data provided by Fyers | Refresh rate: 1 second"

## Real-Time Data (WebSocket)
- Connects to `ws://localhost:8000/ws/live?token={JWT}`
- Parses incoming stock data updates and refreshes the table
- Auto-reconnect on disconnect (every 5s, max 5 attempts)
- Ping every 30s to keep connection alive
- Connection status shown in header

## Architecture & Quality
- Separate component files: Login, Dashboard, Header, StatsCards, ControlsBar, StockTable
- Custom `useWebSocket` hook for all WebSocket logic
- TypeScript interfaces for all data types
- Utility functions for currency (₹), large numbers, percentages, time formatting
- Memoized sorting/filtering for performance
- Protected route pattern with localStorage JWT handling
- Full dark theme with custom CSS variables matching the Bloomberg-inspired palette

