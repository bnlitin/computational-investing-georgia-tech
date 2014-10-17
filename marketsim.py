'''
Market Simulator for Computational Investing Class - Georgia Tech

Author: Boris Litinsky
Date: 10/15/2014
'''

import pandas as pd
import numpy as np
import math
import copy
import QSTK.qstkutil.qsdateutil as du
import datetime as dt
import QSTK.qstkutil.DataAccess as da
import QSTK.qstkutil.tsutil as tsu
import QSTK.qstkstudy.EventProfiler as ep
import sys
import csv

# get command line options
def get_cmdline_options():
    try:
        cash = float(sys.argv[1])
    except:
        cash = float(1000000.00)
        
    try:
        infile = sys.argv[2]
    except:
        infile = "orders.csv"
        
    try:
        outfile = sys.argv[3]
    except:
        outfile = "values.csv"

    print "cmdline options: cash=%d infile=%s outfile=%s" % (cash,infile,outfile)
    return cash,infile,outfile   

#open csv file and read in all stock orders in a numpy array
def read_orders_csvfile(infile):
    orders = []   
    f = open(infile,"rU")
    try:
        reader = csv.reader(f)
        for row in reader:
            orders.append(row[0:6])
    finally:
        f.close()
    return np.asarray(orders)   

#open csv file and write out all transactions
def write_values_csvfile(outfile,fund):
    f = open(outfile,"wb")
    try:
        writer = csv.writer(f,delimiter=',')
        for row in fund:
            writer.writerow(row)
    finally:
        f.close()
     
# read stock database from Yahoo and return data structure
def read_stock_database(start,end,ls_symbols):
    print "read_stock_database"
    dt_start = dt.datetime(int(start[0]),int(start[1]),int(start[2]))
    dt_end   = dt.datetime(int(end[0]),int(end[1]),int(end[2])) + dt.timedelta(days=1)

    ldt_timestamps = du.getNYSEdays(dt_start, dt_end, dt.timedelta(hours=16))    
    
    dataobj = da.DataAccess('Yahoo', cachestalltime=0)
    ls_keys = ['open', 'high', 'low', 'close', 'volume', 'actual_close']
    ldf_data = dataobj.get_data(ldt_timestamps, ls_symbols, ls_keys)   
    d_data = dict(zip(ls_keys, ldf_data))
   
    for s_key in ls_keys:
        d_data[s_key] = d_data[s_key].fillna(method='ffill')
        d_data[s_key] = d_data[s_key].fillna(method='bfill')
        d_data[s_key] = d_data[s_key].fillna(1.0)    
     
    return ldt_timestamps, d_data   

# execute stock order
def execute_order(portfolio,df_close,i,timestamp,np_orders):    
    for order in np_orders:
        order_date  = dt.date(int(order[0]),int(order[1]),int(order[2]))
        order_stock = str(order[3]).upper()
        order_type  = str(order[4]).upper()
        order_quantity = float(order[5])
        
        if timestamp.date() == order_date:
            order_price = df_close[order_stock].ix[df_close.index[i]]
            if order_type == "BUY":               
                portfolio["cash"] -= float(order_quantity * order_price)
                try:
                    portfolio[order_stock] += order_quantity
                except KeyError:
                    portfolio[order_stock] = order_quantity
                print "%s Buying %.0f shares of %s at %0.2f | cash=%0.2f" % (order_date,order_quantity,order_stock,order_price,portfolio["cash"])
            elif order_type == "SELL":
                portfolio["cash"] += float(order_quantity * order_price)
                try:
                    portfolio[order_stock] -= order_quantity
                except KeyError:
                    portfolio[order_stock] = -order_quantity
                print "%s Selling %.0f shares of %s at %0.2f | cash=%0.2f" % (order_date,order_quantity,order_stock,order_price,portfolio["cash"])
    return portfolio

# calculate daily fund value and return it
def calculate_daily_fund_value(portfolio,df_close,i,date):    
    total = float(0.0)
    for stock in portfolio.keys():
        if stock == "cash":
            total += float(portfolio[stock])
        else:
            total += float(portfolio[stock]) * float(df_close[stock].ix[df_close.index[i]])
    
    row = [date.year, date.month, date.day, total]
    return row
                
# process stock orders
def process_stock_orders(ls_symbols, ldt_timestamps, d_data, cash, np_orders):
    print "process_stock_orders"    

    # initialize portfolio and fund
    portfolio = { "cash" : cash }
    fund = []
        
    df_close = d_data['actual_close']

    # Time stamps for the event range
    for i in range(0, len(df_close.index)):
        portfolio = execute_order(portfolio,df_close,i,ldt_timestamps[i],np_orders)                   
        row = calculate_daily_fund_value(portfolio,df_close,i,ldt_timestamps[i])
        fund.append(row)
    return portfolio,fund

# main routine    
def main():
    print "marketsim.py main"
    
    # get command line parameters
    cash,infile,outfile = get_cmdline_options()
    
    # read orders csvfile into a numpy array and get list of stocks traded
    np_orders = read_orders_csvfile(infile)
    ls_symbols = set(list(np_orders[:,3]))

    # determine the earliest and latest start dates
    start = np_orders[0][0:3]
    end   = np_orders[-1][0:3]

    # read stock database from Yahoo
    ldt_timestamps, d_data = read_stock_database(start,end,ls_symbols)
           
    # loop for all NYSE stock days earliest to latest
    portfolio, fund = process_stock_orders(ls_symbols, ldt_timestamps, d_data, cash, np_orders)

    # write out csvfile
    write_values_csvfile(outfile,fund)
    
    print portfolio
    
if __name__ == '__main__':
    main()