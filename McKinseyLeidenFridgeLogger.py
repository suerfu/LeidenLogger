import xlwt
import xlrd
import datetime
import time
from LakeShore372Logger import LakeShore
from TPG366Logger import TPG
from LevelMeterLM510Logger import LevelMeter

sleeptime = 3 # refresh interval = 3 seconds

print('Please do not open the excel files when running this script.')

def getNumberDate(date_only = False):
    year = datetime.datetime.now().year
    month = datetime.datetime.now().month
    day = datetime.datetime.now().day
    hour = datetime.datetime.now().hour
    minute = datetime.datetime.now().minute
    second = datetime.datetime.now().second
    
    date = [year, month, day, hour, minute, second] 

    if date_only == False:
        numberdate = second + 100*minute + 10000*hour + 1000000*day + 100000000*month + 10000000000*year #date and time as a number, IE 20150915104323
        
    if date_only == True:
        numberdate = day + 100*month + 10000*year #date as a number, IE 20150915

    return numberdate

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

def write_excel(interval = sleeptime, line_max = None):
    # init the excel file
    f = xlwt.Workbook()

    # Set the format of time
    #date_format = f.add_format({'num_format': 'dd/mm/yy/ hh:mm:ss'})

    sheet1 = f.add_sheet('Data', cell_overwrite_ok=True)
    row0 = ['Time', 'Temperature Channel 1 (K)', 'Temperature Channel 2 (K)', 'Temperature Channel 3 (K)',
        'Temperature Channel 4 (K)', 'Temperature Channel 5 (K)', 'Temperature Channel 6 (K)', 'Temperature Channel 7 (K)',
        'Temperature Channel 8 (K)', 'Pressure Channel 1 (hPa)', 'Pressure Channel 2 (hPa)', 'Pressure Channel 3 (hPa)', 
        'Pressure Channel 4 (hPa)', 'Pressure Channel 5 (hPa)', 'Pressure Channel 6 (hPa)', 'Level Channel 1 (cm)', 'Level Channel 2 (cm)']
    # Write the first row
    for i in range(0,len(row0)):
        sheet1.write(0,i,row0[i],set_style('Times New Roman',220,True))
    
    temperature = LakeShore("\\\\.\\COM4")
    pressure = TPG("\\\\.\\COM5")
    level = LevelMeter("\\\\.\\COM6")

    # Datetime format
    dateFormat = xlwt.XFStyle()
    dateFormat.num_format_str = 'yyyy/mm/dd hh:mm:ss' 
    
    # Write the data into the xls
    row = 1 # Starting from the second row
    col = len(row0) - 1 
    while True:
        temperatures = [temperature.readTemp(channel = 1), temperature.readTemp(channel = 2), temperature.readTemp(channel = 3),
            temperature.readTemp(channel = 4), temperature.readTemp(channel = 5), temperature.readTemp(channel = 6),
            temperature.readTemp(channel = 7), temperature.readTemp(channel = 8)]
        pressures = [pressure.readPressure(channel = 1), pressure.readPressure(channel = 2), pressure.readPressure(channel = 3),
            pressure.readPressure(channel = 4), pressure.readPressure(channel = 5), pressure.readPressure(channel = 6)]
        levels = [level.readLevel(channel = 1), level.readLevel(channel = 2)]
        line = temperatures + pressures + levels

        # write the current time
        sheet1.write(row, 0, datetime.datetime.now(), dateFormat) 

        # write the measurements
        for j in range(col):
            sheet1.write(row, j + 1, line[j])

        # save the xls once finish writing one line    
        f.save('logger_test_{time}.xls'.format(time = getNumberDate(date_only = True)))

        row += 1
        # exit when enough data (depends on line_max) has been collected
        if row == line_max:
            exit()

if __name__ == '__main__':
    write_excel()


import datetime as dt
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# Create figure for plotting
fig = plt.figure()
ax = fig.add_subplot(1, 1, 1)
xs = []
ys = []
temperature = LakeShore("\\\\.\\COM4")

# This function is called periodically from FuncAnimation
def animate(i, xs, ys):

    # Read temperature (Celsius) from the Fridge
    temp = temperature.readTemp(channel = 1)

    # Add x and y to lists
    xs.append(dt.datetime.now().strftime('%H:%M:%S'))
    ys.append(temp_c)

    # Limit x and y lists to 20 items
    xs = xs[-20:]
    ys = ys[-20:]

    # Draw x and y lists
    ax.clear()
    ax.plot(xs, ys)

    # Format plot
    plt.xticks(rotation=45, ha='right')
    plt.subplots_adjust(bottom=0.30)
    plt.title('Leiden Fridge Temperature over Time')
    plt.ylabel('Temperature (K)')

# Set up plot to call animate() function periodically
ani = animation.FuncAnimation(fig, animate, fargs=(xs, ys), interval=1000)
plt.show()
