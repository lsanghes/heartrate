from ant.easy.node import Node
from ant.easy.channel import Channel
from twilio.rest import Client
from collections import deque
import sys, time, datetime

class Alert:
    def __init__(self, account_sid, auth_token, twilio_number, twilio_call_url, alert_numbers):
        self.client = Client(account_sid, auth_token)
        self.twilio_number = twilio_number
        self.twilio_call_url = twilio_call_url
        self.alert_numbers = alert_numbers

    def send_sms(self, content):
        msg = ""
        for number in self.alert_numbers:
            try:
                message = self.client.messages.create(to=number, from_=self.twilio_number, body=content)
                msg += "SMS:{} SENT\n".format(number)
            except Exception as ex:
                print(ex)
                msg += "SMS:{} FAILED\n".format(number)
        return msg

    def make_call(self):
        msg = ""
        for number in self.alert_numbers:
            try:
                call = client.api.account.calls.create(to=number, from_=self.twilio_number, url=self.twilio_call_url)
                msg += "Call:{} SENT\n".format(number)
            except Exception as ex:
                print(ex)
                msg += "Call:{} FAILED\n".format(number)
        return msg


class HRM:
    def __enter__(self):
        return self

    def __exit__(self, type_, value, traceback):
        if self.antnode:
            self.antnode.stop()

    def __init__(self, netkey, alert, sampling_interval, moving_avg_size, max_hr_threshold, enable_sms_alert, enable_call_alert):
        self.alert = alert
        self.prev_timestamp = time.time()
        self.prev_avg_hr = 0
        self.netkey = netkey
        self.antnode = None
        self.channel = None
        self.sms_enabled = True
        self.call_enabled = False
        self.past_heartrates = deque([], moving_avg_size)
        self.curr_heartrate = None
        self.sampling_interval = sampling_interval
        self.max_hr_threshold = max_hr_threshold
        self.enable_call_alert = enable_call_alert
        self.enable_sms_alert = enable_sms_alert

    def start(self):
        print("starting...")
        self.setup_node_channel()
        self.channel.open()
        self.antnode.start()
        print("start listening for hr events")

    def setup_node_channel(self):
        self.antnode = Node()
        self.antnode.set_network_key(0x00, self.netkey)
        self.channel = self.antnode.new_channel(Channel.Type.BIDIRECTIONAL_RECEIVE)
        self.channel.on_broadcast_data = self.process
        self.channel.on_burst_data = self.process
        self.channel.set_period(8070)
        self.channel.set_search_timeout(12)
        self.channel.set_rf_freq(57)
        self.channel.set_id(0, 120, 0)

    def process(self, data):
        current_timestamp = time.time()
        if current_timestamp - self.prev_timestamp < self.sampling_interval:
            return

        ts = datetime.datetime.fromtimestamp(current_timestamp).strftime("%Y%m%d-%H:%M:%S")
        hr = data[7]
        self.past_heartrates.append(hr)
        curr_avg_hr = sum(self.past_heartrates) // len(self.past_heartrates)

        # log hr
        message = "{},{},{}".format(ts, hr, curr_avg_hr)
        with open("hr_log.csv", "a") as f:
            print(message)
            f.write(message + "\n")

        # detect abnormal hr
        if self.prev_avg_hr < self.max_hr_threshold and curr_avg_hr > self.max_hr_threshold:
            if self.enable_sms_alert:
                ts = datetime.datetime.fromtimestamp(current_timestamp).strftime("%I:%M%p")
                smsbody =  "Unusual HR of {} BPM was detected at {}.".format(hr, ts)
                print(smsbody)
                print(self.alert.send_sms(smsbody))

            if self.enable_call_alert:
                print(self.alert.make_call())

        # update prev_* values
        self.prev_timestamp = current_timestamp
        self.prev_avg_hr = curr_avg_hr


netkey = [0xb9, 0xa5, 0x21, 0xfb, 0xbd, 0x72, 0xc3, 0x45]
twilio_call_url = "http://twimlets.com/holdmusic?Bucket=com.twilio.music.ambient"
account_sid = "AC36f913e555e5e0760cf5edfe1fd528f2"
auth_token  = "5c9aa78c852e24fd239ce1bfe3f5b918"
twilio_number = "+13124710394"
alert_numbers = ["+13123162187"]
sampling_interval = 5
moving_avg_size = 6
enable_sms_alert = 1
enable_call_alert = 0
max_hr_threshold = 105
alert = Alert(account_sid, auth_token, twilio_number, twilio_call_url, alert_numbers)

with HRM(netkey, alert, sampling_interval, moving_avg_size, max_hr_threshold, enable_sms_alert, enable_call_alert) as hrm:
    hrm.start()
    try:
        hrm.start()
    except:
        print("...exception...")


# def api_call_monitor():
#     global last_api_stamp
#     curr_timestamp = time.time()
#     ts = datetime.datetime.fromtimestamp(curr_timestamp).strftime("%Y%m%d_%H%M%S")
#     since_last_heartbeat = int(curr_timestamp - last_api_stamp)
#     if since_last_heartbeat > min_freq:
#         if self.enable_sms_alert:
#             smsbody = "{} : WARNIG last heart beat was received {} sec ago!".format(ts, since_last_heartbeat)
#             print(smsbody)
#             print(self.alert.send_sms(smsbody))
#     else:
#         print("{} : Heart beat status is OK".format(ts, since_last_heartbeat))

# scheduler = BackgroundScheduler()
# scheduler.start()
# scheduler.add_job(func=api_call_monitor, trigger=IntervalTrigger(seconds=monitor_task_interval_sec))

# # Shut down the scheduler when exiting the app
# atexit.register(lambda: scheduler.shutdown())

