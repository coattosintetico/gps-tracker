# gps-tracker
Save location locally periodically.

I had to enable Termux to run on the background so that the script doesn't stop working when putting device to sleep:
```
battery > battery usage by app > termux > allow background activity
```

FUCK and also it requires to grant permission to Termux to ALWAYS have access to location:
```
Apps > Termux:API > Permissions > Location > Allow all the time
```

It also acquires the wakelock at the beginning of the script in order to prevent it from shutting down.

Otherwise, alternative: [GPSLogger](https://f-droid.org/en/packages/com.mendhak.gpslogger/). But seems like for now it's working properly :).
