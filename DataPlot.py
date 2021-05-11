import datetime as dt
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from LakeShore372Logger import LakeShore
from TPG366Logger import TPG
import time
import xlwt
#from LevelMeterLM510Logger import LevelMeter

print('Leiden Fridge Data Logger, McKinsey Helium Group, UC Berkeley')
print('by Lanqing Yuan')
print('Please switch to channel 6 on LakeShore to pause the auto channel switch.')

# Set the first row's format
def set_style(name,height,bold=False):
    style = xlwt.XFStyle()
    font = xlwt.Font()
    font.name = name
    font.bold = bold
    font.color_index = 4
    font.height = height
    style.font = font
    return style

# Create figure for plotting
xs = []
y1s = []
y2s = []
y3s = []
y4s = []
y5s = []
y6s = []
y7s = []
y8s = []
y9s = []
y10s = []
y11s = []
y12s = []

try:
    temperature = LakeShore("\\\\.\\COM4")
except:
    print('COM4 temperature detector is not physically connected or there are connection errors')
try:
    pressure = TPG("\\\\.\\COM5")
except:    
    print('COM5 pressure detector is not physically connected or there are connection errors')
try:
    level = LevelMeter("\\\\.\\COM6")
except:    
    print('COM6 level detector is not physically connected or there are connection errors')

fig = plt.figure()
ax1 = fig.add_subplot(2, 3, 1)
ax2 = ax1.twinx()
ax3 = fig.add_subplot(2, 3, 2)
ax4 = ax3.twinx()
ax5 = fig.add_subplot(2, 3, 3)
ax6 = ax5.twinx()
ax7 = fig.add_subplot(2, 3, 4)
ax8 = ax7.twinx()
ax9 = fig.add_subplot(2, 3, 5)
ax10 = ax9.twinx()
ax11 = fig.add_subplot(2, 3, 6)

f = xlwt.Workbook()
sleeptime = 3
sheet1 = f.add_sheet('Data', cell_overwrite_ok=True)

row0 = ['Time', 'Temperature Channel 1 (K)', 'Temperature Channel 2 (K)', 'Temperature Channel 3 (K)', 'Tmeperature Channel 4 (K)'
         'Pressure Channel 1 (hPa)', 'Pressure Channel 2 (hPa)', 'Pressure Channel 3 (hPa)', 
        'Pressure Channel 4 (hPa)', 'Pressure Channel 5 (hPa)', 'Pressure Channel 6 (hPa)']
for i in range(0,len(row0)):
        sheet1.write(0,i,row0[i],set_style('Times New Roman',220,True))
        
# Datetime format
dateFormat = xlwt.XFStyle()
dateFormat.num_format_str = 'yyyy/mm/dd hh:mm:ss' 
    
# Write the data into the xls
row = 1 # Starting from the second row
col = len(row0) - 1 

def getNumberDate(date_only = False):
    year = dt.datetime.now().year
    month = dt.datetime.now().month
    day = dt.datetime.now().day
    hour = dt.datetime.now().hour
    minute = dt.datetime.now().minute
    second = dt.datetime.now().second
    
    date = [year, month, day, hour, minute, second] 

    if date_only == False:
        numberdate = second + 100*minute + 10000*hour + 1000000*day + 100000000*month + 10000000000*year #date and time as a number, IE 20150915104323
        
    if date_only == True:
        numberdate = day + 100*month + 10000*year #date as a number, IE 20150915

    return numberdate

# To check whether the measure value make sense.
def checknone(measure):
    if measure == 0 or measure == None:
        return True
    else:
        return False

pp = 1 # swtich on

# This function is called periodically from FuncAnimation
def animate(i, xs, y1s, y2s, y3s, y4s, y5s, y6s, y7s, y8s, y9s, y10s, y11s, y12s):
    
    global row
    global pp
    
    '''
    print('Pause or continue?')
    Pause = input()
    if Pause == 'p':
        pp = 0
    if Pause == 'c':
        pp = 1
    '''

    # Read temperature (K) from the Fridge
    # In case we have mK as unit
    try:
        temp1 = temperature.readTemp(channel = 1, pause = pp)
    except:
        temp1 = 0
    time.sleep(5)
    if temp1 >= 300:
        temp1 = 0.001 * temp1
    if checknone(temp1):
        temp1 = 0
    
    try:
        temp2 = temperature.readTemp(channel = 2, pause = pp)
    except:
        temp2 = 0
    time.sleep(5)
    if temp2 >= 300:
        temp2 = 0.001 * temp2
    if checknone(temp2):
        temp2 = 0
        
    try:
        temp3 = temperature.readTemp(channel = 3, pause = pp)
    except:
        temp3 = 0
    time.sleep(5)
    if temp3 >= 300:
        temp3 = 0.001 * temp3
    if checknone(temp3):
        temp3 = 0
        
    try:
        temp4 = temperature.readTemp(channel = 4, pause = pp)
    except:
        temp4 = 0
    time.sleep(5)
    if temp4 >= 300:
        temp4 = 0.001 * temp4
    if checknone(temp4):
        temp4 = 0
    
    temperatures = [temp1, temp2, temp3, temp4]

    # Read pressures
    try:
        pressure1 = pressure.readPressure(channel = 1)
    except:
        pressure1 = 0
    if checknone(pressure1):
        pressure1 = 0
    if pressure1 == 0 and len(y5s) > 1:
        pressure1 == y5s[-1]
        
    try:
        pressure2 = pressure.readPressure(channel = 2)
    except:
        pressure2 = 0
    if checknone(pressure2):
        pressure2 = 0
    if pressure2 == 0 and len(y6s) > 1:
        pressure2 == y6s[-1]

    try:
        pressure3 = pressure.readPressure(channel = 3)
    except:
        pressure3 = 0
    if checknone(pressure3):
        pressure3 = 0
    if pressure3 == 0 and len(y7s) > 1:
        pressure3 == y7s[-1]
        
    try:
        pressure4 = pressure.readPressure(channel = 4)
    except:
        pressure4 = 0
    if checknone(pressure4):
        pressure4 = 0
    if pressure4 == 0 and len(y8s) > 1:
        pressure4 == y8s[-1]

    try:
        pressure5 = pressure.readPressure(channel = 5)
    except:
        pressure5 = 0
    if checknone(pressure5):
        pressure5 = 0
    if pressure5 == 0 and len(y9s) > 1:
        pressure5 == y9s[-1]

    try:
        pressure6 = pressure.readPressure(channel = 6)
    except:
        pressure6 = 0
    if checknone(pressure6):
        pressure6 = 0
    if pressure6 == 0 and len(y10s) > 1:
        pressure6 == y10s[-1]

    pressures = [pressure1, pressure2, pressure3, pressure4, pressure5, pressure6]
    
    # Read levels
    try:
        level1 = level.readLevel(channel = 1)
    except:
        level1 = 0
    if checknone(level1):
        level1 = 0
    if level1 == 0 and len(y11s) > 1:
        level1 == y11s[-1]

    try:
        level2 = level.readLevel(channel = 2)
    except:
        level2 = 0
    if checknone(level2):
        level2 = 0
    if level2 == 0 and len(y12s) > 1:
        level2 == y12s[-1]
    
    levels = [level1, level2]

    line = temperatures + pressures + levels
    
    sheet1.write(row, 0, dt.datetime.now(), dateFormat)
    
    for j in range(col):
            sheet1.write(row, j + 1, line[j])
            
    # save the xls once finish writing one line    
    f.save('logger_test_{time}.xls'.format(time = getNumberDate(date_only = True)))
    row += 1
    # Write in data here!
    
    # Add x and y to lists
    xs.append(dt.datetime.now().strftime('%H:%M:%S'))
    
    if temp1 == 0 and len(y1s) > 0:
        temp1_modified = y1s[-1]
    else:
        temp1_modified = temp1
    y1s.append(temp1_modified)

    if temp2 == 0 and len(y2s) > 0:
        temp2_modified = y2s[-1]
    else:
        temp2_modified = temp2
    y2s.append(temp2_modified)

    if temp3 == 0 and len(y3s) > 0:
        temp3_modified = y3s[-1]
    else:
        temp3_modified = temp3
    y3s.append(temp3_modified)

    if temp4 == 0 and len(y4s) > 0:
        temp4_modified = y4s[-1]
    else:
        temp4_modified = temp4
    y4s.append(temp4_modified)

    y5s.append(pressure1)
    y6s.append(pressure2)
    y7s.append(pressure3)
    y8s.append(pressure4)
    y9s.append(pressure5)
    y10s.append(pressure6)
    y11s.append(level1)
    y12s.append(level2)


    # Limit x and y lists to 15 items
    xs = xs[-15:]
    y1s = y1s[-15:]
    y2s = y2s[-15:]
    y3s = y3s[-15:]
    y4s = y4s[-15:]
    y5s = y5s[-15:]
    y6s = y6s[-15:]
    y7s = y7s[-15:]
    y8s = y8s[-15:]
    y9s = y9s[-15:]
    y10s = y10s[-15:]
    y11s = y11s[-15:]
    y12s = y12s[-15:]

    ax1.clear()
    ax2.clear() # maybe problematic
    ax1.plot(xs, y1s, label = 'Chan 1', color = 'r')
    ax1.set_ylabel('Chan1 (K)')
    ax1.legend()
    ax2.plot(xs, y2s, label = 'Chan 2', color = 'b')
    ax2.set_ylabel('Chan2 (K)')
    ax2.legend()
    plt.xticks(rotation=45, ha='right')
    ax1.set_title('Leiden Fridge Temperature over Time')

    ax3.clear()
    ax4.clear() # maybe problematic
    ax3.plot(xs, y3s, label = 'Chan 3', color = 'r')
    ax3.set_ylabel('Chan3 (K)')
    ax3.legend()
    ax4.plot(xs, y4s, label = 'Chan 4', color = 'b')
    ax4.set_ylabel('Chan4 (K)')
    ax4.legend()
    plt.xticks(rotation=45, ha='right')
    ax3.set_title('Leiden Fridge Temperature over Time')
    

    ax5.clear()
    ax6.clear() # maybe problematic
    ax5.plot(xs, y5s, label = 'Chan 1', color = 'r')
    ax5.set_ylabel('Chan1 (hPa)')
    ax5.legend()
    ax6.plot(xs, y6s, label = 'Chan 2', color = 'b')
    ax6.set_ylabel('Chan2 (hPa)')
    ax6.legend()
    plt.xticks(rotation=45, ha='right')
    ax5.set_title('Leiden Fridge Pressures over Time')
    
    ax7.clear()
    ax8.clear() # maybe problematic
    ax7.plot(xs, y7s, label = 'Chan 3', color = 'r')
    ax7.set_ylabel('Chan3 (hPa)')
    ax7.legend()
    ax8.plot(xs, y8s, label = 'Chan 4', color = 'b')
    ax8.set_ylabel('Chan4 (hPa)')
    ax8.legend()
    plt.xticks(rotation=45, ha='right')
    ax7.set_title('Leiden Fridge Pressures over Time')
    
    ax9.clear()
    ax10.clear() # maybe problematic
    ax9.plot(xs, y9s, label = 'Chan 5', color = 'r')
    ax9.set_ylabel('Chan5 (hPa)')
    ax9.legend()
    ax10.plot(xs, y10s, label = 'Chan 6', color = 'b')
    ax10.set_ylabel('Chan6 (hPa)')
    ax10.legend()
    plt.xticks(rotation=45, ha='right')
    ax9.set_title('Leiden Fridge Pressures over Time')    
    
    ax11.clear()
    ax11.plot(xs, y11s, label = 'Chan 1', color = 'r')
    ax11.plot(xs, y12s, label = 'Chan 2', color = 'b')
    ax11.legend()
    ax11.set_ylabel('Level (cm)')
    ax11.set_title('Leiden Fridge Levels over time')

    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
    plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45)
    plt.setp(ax5.xaxis.get_majorticklabels(), rotation=45)
    plt.setp(ax7.xaxis.get_majorticklabels(), rotation=45)
    plt.setp(ax9.xaxis.get_majorticklabels(), rotation=45)
    plt.setp(ax11.xaxis.get_majorticklabels(), rotation=45)

ani = animation.FuncAnimation(fig, animate, fargs=(xs, y1s, y2s, y3s, y4s, y5s, 
                                                   y6s, y7s, y8s, y9s, y10s, y11s, y12s), interval=40000)
plt.show()