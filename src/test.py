import datetime
from backports.zoneinfo import ZoneInfo

dt_now = datetime.datetime.now()

bary_y = dt_now.year.to_bytes(2, 'big')
bary_dt = bytearray((dt_now.month, dt_now.day, dt_now.hour, dt_now.minute, dt_now.second, datetime.date.today().isoweekday(), dt_now.microsecond//1000*256//1000, 0))

print(bary_y)
print(' '.join('{:02x}'.format(x) for x in bary_y))
print(bary_dt)
print(datetime.date.today().isoweekday())
print(dt_now.microsecond//1000*256//1000)

print(' '.join('{:02x}'.format(x) for x in (bary_y + bary_dt)))
print(len(bary_y + bary_dt))


tzoffset = int(datetime.datetime.now(ZoneInfo('Asia/Tokyo')).utcoffset().total_seconds() / 60 / 15)
print(tzoffset)
dstoffset = int(datetime.datetime.now(ZoneInfo('Asia/Tokyo')).dst().total_seconds() / 60 / 15)
print(dstoffset)
bary_tzdst_info = bytearray((tzoffset, dstoffset))
print(' '.join('{:02x}'.format(x) for x in bary_tzdst_info))
