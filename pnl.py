from datetime import datetime

count = 0
position = 0
open_buy = 0.
open_sell = 0.
pnl = 0.
monthly = 0.
annual = 0.
max_risk = 5
prev_date = datetime.today()
risk_exceeded = False

with open('data/a_pnl.csv', 'w') as w:
    with open('data/results.csv') as f:
        prev_day = 100
        for line in f:
            count += 1
            if count == 1:
                w.write(line)
                continue
            parts = line.split(',')
            date = datetime.strptime(parts[0], '%Y%m%d')
            days = int(parts[4])
            future_close = float(parts[2])
            roll = float(parts[5])

            if position > 0 and (open_buy - future_close) > max_risk:
                position = 0
                open_buy = 0
                pnl += future_close
                monthly += future_close
                annual += future_close

                line = line.rstrip('\n') + ',{},CB,{}, {}, {}\n' \
                    .format(str(future_close), '', '', round(pnl, 2))
                print("Profit: %s" % monthly)
                risk_exceeded = True

            if position < 0 and (future_close - open_sell) > max_risk:
                position = 0
                open_sell = 0
                pnl -= future_close
                monthly -= future_close
                annual -= future_close

                line = line.rstrip('\n') + ',{},CS,{},{},{}\n' \
                    .format(str(-1 * future_close), '', '', round(pnl, 2))
                print("Profit: %s" % monthly)
                risk_exceeded = True

            if (date - prev_date).days > 5:
                print('ERROR: Gap %s - %s' % (prev_date, date))
            if roll > 0.1 and position > -1 and days > 1 and not risk_exceeded:
                position -= 1
                open_sell = future_close
                pnl += future_close
                monthly += future_close
                annual += future_close
                line = line.rstrip('\n') + ',%s,SELL,,\n' % (str(future_close))
            elif roll < -0.1 and position < 1 and days > 1 and not risk_exceeded:
                position += 1
                open_buy = future_close
                pnl -= future_close
                monthly -= future_close
                annual -= future_close
                line = line.rstrip('\n') + ',%s,BUY,\n' % (str(-1 * future_close))
            elif days == 1 and position < 0 and not risk_exceeded:
                position = 0
                open_sell = 0
                pnl -= future_close
                monthly -= future_close
                annual -= future_close
                print_anal = str(round(annual, 2)) if date.month == 12 else ''
                line = line.rstrip('\n') + ',{},CS,{},{},{}\n' \
                    .format(str(-1 * future_close), round(monthly, 2), print_anal, round(pnl, 2))
                print("Profit: %s" % monthly)
                monthly = 0
                if date.month == 12:
                    annual = 0.
            elif days == 1 and position > 0 and not risk_exceeded:
                position = 0
                open_buy = 0
                pnl += future_close
                monthly += future_close
                annual += future_close
                print_anal = str(round(annual, 2)) if date.month == 12 else ''
                line = line.rstrip('\n') + ',{},CB,{}, {}, {}\n' \
                    .format(str(future_close), round(monthly, 2), print_anal, round(pnl, 2))
                print("Profit: %s" % monthly)
                monthly = 0
                if date.month == 12:
                    annual = 0.
            elif days == 1:
                print_anal = str(round(annual, 2)) if date.month == 12 else ''
                line = line.rstrip('\n') + ',,CB,{}, {}, {}\n'.format(round(monthly, 2), print_anal,
                                                                      round(pnl, 2))
                print("Profit: %s" % monthly)
                monthly = 0
                risk_exceeded = False
                if date.month == 12:
                    annual = 0.
            prev_day = days
            prev_date = date
            w.write(line)
        print("PnL: %s" % pnl)
