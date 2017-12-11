from ant.easy.node import Node
from ant.easy.channel import Channel
from twilio.rest import Client
from collections import deque
from datetime import datetime
import time, logging

class Alert:
    def __init__(self, account_sid, auth_token, twilio_number, twilio_call_url, alert_numbers):
        self.client = Client(account_sid, auth_token)
        self.twilio_number = twilio_number
        self.twilio_call_url = twilio_call_url
        self.alert_numbers = alert_numbers
        self.logger = logging.getLogger("Alert")

    def send_sms(self, msg):
        ret = ""
        for number in self.alert_numbers:
            try:
                response = self.client.messages.create(to=number, from_=self.twilio_number, body=msg)
                self.logger.debug(response)
                ret += "SMS:{} SENT\n".format(number)
            except Exception as ex:
                self.logger.error('{}: {}'.format(type(ex), ex))
                ret += "SMS:{} FAILED\n".format(number)
        return ret

    def make_call(self, msg):
        ret = ""
        for number in self.alert_numbers:
            try:
                response = self.client.api.account.calls.create(to=number, from_=self.twilio_number, url=self.twilio_call_url)
                self.logger.debug(response)
                ret += "Call:{} SENT\n".format(number)
            except Exception as ex:
                self.logger.error('{}: {}'.format(type(ex), ex))
                ret += "Call:{} FAILED\n".format(number)
        return ret


class HRM:
    def __init__(self, netkey, alert, sampling_freq, moving_avg_size, resting_hr, warning_hr, critical_hr):
        self.logger = logging.getLogger("HRM")
        # ant+ config
        self.netkey = netkey
        self.antnode = None
        self.channel = None
        # alert config
        self.alert = alert
        self.warning_hr = warning_hr
        self.critical_hr = critical_hr
        self.alert_ts = 0
        # processing config
        self.prev_ts = time.time()
        self.past_heartrates = deque([resting_hr] * moving_avg_size, moving_avg_size)
        self.sampling_freq = sampling_freq


    def stop(self):
        if self.antnode:
            self.antnode.stop()

    def start(self):
        self.setup_node_channel()
        self.channel.open()
        self.antnode.start()

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
        curr_ts = time.time()
        curr_ts_fmt = datetime.fromtimestamp(curr_ts).strftime("%m/%d/%Y %H:%M:%S")
        if curr_ts - self.prev_ts < self.sampling_freq:
            return

        hr = data[7]
        self.past_heartrates.append(hr)
        curr_avg_hr = sum(self.past_heartrates) // len(self.past_heartrates)

        self.logger.info("hr={}, cur_avg_hr={}, warning_hr={}, critical_hr={}, alert_ts={}".format(hr, curr_avg_hr, self.warning_hr, self.critical_hr, self.alert_ts))

        # log hr for analysis
        hr_log = "{},{},{}".format(curr_ts_fmt, hr, curr_avg_hr)
        with open("hr_log.csv", "a") as f:
            f.write(hr_log + "\n")

        # critical heart rate, call & sms every 1 min
        if curr_avg_hr > self.critical_hr:
            msg =  "Critical: HR of {} BPM was detected at {}.".format(hr, curr_ts_fmt)
            self.logger.info(msg)
            if time.time() - self.alert_ts > 60:
                self.logger.info(self.alert.send_sms(msg))
                self.logger.info(self.alert.make_call(msg))
                self.alert_ts = curr_ts
            else:
                self.logger.info("alert was sent less than 60 seconds ago, no alert will be sent.")

        # warning heart rate, sms every minute 5 min
        elif curr_avg_hr > self.warning_hr:
            msg =  "Warning: HR of {} BPM was detected at {}.".format(hr, curr_ts_fmt)
            self.logger.info(msg)
            if time.time() - self.alert_ts > 60 * 5:
                self.logger.info(self.alert.send_sms(msg))
                self.alert_ts = curr_ts
            else:
                self.logger.info("alert was sent less than 5 min ago, no alert will be sent.")
        self.prev_ts = curr_ts

netkey = [0xb9, 0xa5, 0x21, 0xfb, 0xbd, 0x72, 0xc3, 0x45]
twilio_call_url = "https://handler.twilio.com/twiml/EH45d33797a5de5078025c83c420f1df32"
account_sid = 
auth_token  = 
AWSAccessKeyId = 
AWSSecretKey = 
twilio_number = 
alert_numbers = 
sampling_freq = 5
moving_avg_size = 12
resting_hr = 80
warning_hr = 100
critical_hr = 115

def main():
    logging.basicConfig(format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s', level = logging.INFO)
    alert = Alert(account_sid, auth_token, twilio_number, twilio_call_url, alert_numbers.split(";"))
    hrm = HRM(netkey, alert, sampling_freq, moving_avg_size, resting_hr, warning_hr, critical_hr)
    try:
        print("Starting HRM...")
        hrm.start()
    finally:
        print("Stopping HRM...")
        hrm.stop()

if __name__ == "__main__":
    main()
