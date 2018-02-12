
count = 0
open_buy = False
open_sell = False
buy = 0.
sell = 0.
pnl = 0.

with open('data/a_pnl.csv', 'w') as w:
    with open('data/results.csv') as f:
        prev_day = 100
        for line in f:
            count += 1
            if count == 1:
                w.write(line)
                continue
            parts = line.split(',')
            days = int(parts[8])
            future_close = float(parts[6])
            roll = float(parts[9])
            if roll > 0.1 and not open_sell:
                open_sell = True
                sell = future_close
                line = line.rstrip('\n') + ',%s,,SELL,\n' % str(future_close)
            elif roll < -0.1 and not open_buy:
                open_buy = True
                buy = future_close
                line = line.rstrip('\n') + ',%s,,BUY\n' % str(-1*future_close)
            elif (days == 1 or days > prev_day) and open_sell:
                open_sell = False
                line = line.rstrip('\n') + ',%s,%s,CS\n' % (str(-1*future_close), round(sell-future_close, 2))
                print("Profit: %s" % (sell-future_close))
                pnl += (sell-future_close)
            elif (days == 1 or days > prev_day) and open_buy:
                open_buy = False
                line = line.rstrip('\n') + ',%s,%s,CB\n' % (str(future_close), round(future_close - buy, 2))
                print("Profit: %s" % (future_close - buy))
                pnl += (future_close - buy)
            prev_day = days
            w.write(line)
        print("PnL: %s" % pnl)

