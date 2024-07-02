import yfinance as yf
import pandas as pd
from settings import ratios
from enum import Enum
from datetime import datetime, timedelta
from dateutil import tz

class Period(Enum):
    LAST = "LAST"
    MINUTE_AGO = "MINUTE_AGO"
    HOUR_AGO = "HOUR_AGO"
    DAY_AGO = "DAY_AGO"

def resolve_exceptions(df: pd.DataFrame) -> pd.DataFrame:
    # Handle related tickers and merge them into a single row
    tickers_to_merge = {
        'YPF': 'YPFD'
    }
    
    for ticker_usa, ticker_ba in tickers_to_merge.items():
        index_usa = df[df['Ticker'] == ticker_usa].index
        index_ba = df[df['Ticker'] == ticker_ba].index
        
        if not index_usa.empty and not index_ba.empty:
            # Merge the rows
            df.at[index_usa[0], 'Price BA'] = df.at[index_ba[0], 'Price BA']
            df.drop(index_ba, inplace=True)
    
    return df

def get_ticker_adj_close_df(ticker: str) -> pd.DataFrame:

    data=yf.download(ticker,interval="1m", period="5d", progress = False)
    data.index = data.index.tz_convert('America/Argentina/Buenos_Aires')
    data = data.filter(like='Adj Close')

    return data

def get_period_adj_close(df: pd.DataFrame, period: Period) -> float:
    if period == Period.LAST:
        return df['Adj Close'].iloc[-1]
    elif period == Period.MINUTE_AGO:
        return df['Adj Close'].iloc[-2]
    elif period == Period.HOUR_AGO:
        return df['Adj Close'].iloc[-60]
    elif period == Period.DAY_AGO:
        today = datetime.now(tz=tz.gettz(df.index.tz.zone)).date()
        unique_dates = sorted(df.index.date, reverse=True)
        previous_date = None
        
        for date in unique_dates:
            if date < today:
                previous_date = date
                break
        
        if previous_date:
            first_row_previous_date = df[df.index.date == previous_date].iloc[-1]
            return first_row_previous_date['Adj Close']
    
def get_tickers_ccl_at_period_df(all_df: dict[str, pd.DataFrame], period: Period) -> pd.DataFrame:
    data_usa = []
    data_ba = []
    for ticker in all_df.keys():
        df = all_df[ticker]
        adj_close_price = get_period_adj_close(df, period)
        if '.BA' in ticker:
            data_ba.append({
                'Ticker': ticker.replace('.BA', ''),
                'Price BA': round(adj_close_price, 2),
                })
        else:
            data_usa.append({
                'Ticker': ticker,
                'Price USA': round(adj_close_price, 2),
                })
        
    df_usa = pd.DataFrame(data_usa)
    df_ba = pd.DataFrame(data_ba)
    
    result_df = pd.merge(df_usa, df_ba, on='Ticker', how='outer')
    result_df = resolve_exceptions(result_df)
    result_df['Ratio'] = result_df['Ticker'].apply(lambda x: ratios[x] if x in ratios else 1)
    result_df['CCL'] = round(result_df['Price BA'] / result_df['Price USA'] * result_df['Ratio'], 2)
    result_df.drop(columns=['Ratio', 'Price USA', 'Price BA'], inplace=True)
    return result_df

def get_tickers_ccl_df(tickers: list[str]) -> pd.DataFrame:
    all_df = {}
    for ticker in tickers:
        all_df[ticker] = get_ticker_adj_close_df(ticker)
    
    last_df = get_tickers_ccl_at_period_df(all_df, Period.LAST)
    previous_df = get_tickers_ccl_at_period_df(all_df, Period.MINUTE_AGO)
    hour_ago_df = get_tickers_ccl_at_period_df(all_df, Period.HOUR_AGO)
    day_ago_df = get_tickers_ccl_at_period_df(all_df, Period.DAY_AGO)

    result_df = pd.merge(last_df, previous_df, on='Ticker', how='outer', suffixes=('', ' -1m'))
    result_df = pd.merge(result_df, hour_ago_df, on='Ticker', how='outer', suffixes=('', ' -1h'))
    result_df = pd.merge(result_df, day_ago_df, on='Ticker', how='outer', suffixes=('', ' -1d'))

    result_df["% 1m"] = round((result_df['CCL'] - result_df['CCL -1m']) / result_df['CCL -1m'] * 100, 2)
    result_df["% 1h"] = round((result_df['CCL'] - result_df['CCL -1h']) / result_df['CCL -1h'] * 100, 2)
    result_df["% 1d"] = round((result_df['CCL'] - result_df['CCL -1d']) / result_df['CCL -1d'] * 100, 2)

    result_df.drop(columns=['CCL -1m', 'CCL -1h', 'CCL -1d'], inplace=True)
    return result_df

if __name__ == "__main__":
    from settings import tickers
    print(get_tickers_ccl_df(tickers))