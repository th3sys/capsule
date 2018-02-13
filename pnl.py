from datetime import datetime

count = 0
position = 0
pnl = 0.
monthly = 0.
annual = 0.
prev_date = datetime.today()

with open('data/a_pnl.csv', 'w') as w:
    with open('data/results.csv') as f:
        prev_day = 100
        for line in f:
            count += 1
            if count == 1:
                w.write(line)
                continue
            parts = line.split(',')
            date = datetime.strptime(parts[4], '%Y%m%d')
            days = int(parts[8])
            future_close = float(parts[6])
            roll = float(parts[9])
            if roll > 0.1 and position > -1 and days > 1:
                position -= 1
                pnl += future_close
                monthly += future_close
                annual += future_close
                line = line.rstrip('\n') + ',%s,SELL,,\n' % (str(future_close))
            elif roll < -0.1 and position < 1 and days > 1:
                position += 1
                pnl -= future_close
                monthly -= future_close
                annual -= future_close
                line = line.rstrip('\n') + ',%s,BUY,\n' % (str(-1 * future_close))
            elif (days == 1 or days > prev_day) and position < 0:
                position = 0
                pnl -= future_close
                monthly -= future_close
                annual -= future_close
                print_anal = str(round(annual, 2)) if  date.month == 12 else ''
                line = line.rstrip('\n') + ',{},CS,{},{},{}\n' \
                    .format(str(-1 * future_close), round(monthly, 2), print_anal, round(pnl, 2))
                print("Profit: %s" % monthly)
                monthly = 0
                if date.month == 12:
                    annual = 0.
            elif (days == 1 or days > prev_day) and position > 0:
                position = 0
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
                if date.month == 12:
                    annual = 0.
            prev_day = days
            prev_date = date
            w.write(line)
        print("PnL: %s" % pnl)
