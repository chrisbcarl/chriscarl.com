# actual authoritative answers on timezones out here.
# I reverse engineered this shit. ON MY OWN damnit
# TODO: DST crap, probably unecessary but see https://docs.python.org/3.10/library/datetime.html#datetime.tzinfo.fromutc for tzinfo_examples.py
#   because if I re-implement this myself, i'll need a table of timezones and DST's for them and its kinda pointless.
import time
import datetime
import calendar

tzname = time.tzname[0]

greenwich, local = time.gmtime(), time.localtime()
gw_ts, lc_ts = calendar.timegm(greenwich), calendar.timegm(local)
gw_hrs = gw_ts / 3600
lc_hrs = lc_ts / 3600
offset = datetime.timedelta(hours=int(lc_hrs - gw_hrs))

# timezones subclassed and then MADE. there is no table anywhere except in the 3rd party mods
tz = datetime.timezone(offset, name=tzname)

# to timezone aware datetime
now_tz = datetime.datetime.now(tz=tz)
print(now_tz)

# to utc
UTC = datetime.timezone.utc
now_utc = datetime.datetime(
    year=now_tz.year,
    month=now_tz.month,
    day=now_tz.day,
    hour=now_tz.hour,
    minute=now_tz.minute,
    second=now_tz.second,
    microsecond=now_tz.microsecond,
    tzinfo=UTC,
)
now_utc -= offset  # "undo" the offset
print(now_utc)
