import pyshark
import os
from packet_processing.helper_functions import create_logger, helpers
import datetime


class Processor:
    def __init__(self, directory):
        self.directory = directory
        log_filename = self.directory + "/packet_processing.log"

        self.logger = create_logger.create_logger(log_filename, "Packet_processor")
        self.files = None
        self.root = None
        self.results = {}
        self.sub_ids = {}
        self.display_filter = "\
((diameter.flags.request == 1 ) && \
(diameter.CC-Request-Type == 3)) && \
(diameter.Termination-Cause == 3)"

    def find_files(self):
        file_filter = []
        for self.root, dirs, self.files in os.walk(self.directory):
            for file in self.files:
                if file.endswith(".pcap") or file.endswith(".cap") or file.endswith(".pcapng"):
                    self.logger.info("Found %s" % file)
                    file_filter.append(file)
        self.files = file_filter
        return

    def collect_diam_sessions(self):

        for file in self.files:
            # if file != "test.pcap":
            #    continue

            self.results[file] = []
            self.logger.info("Started collect_diam_sessions() for %s" % file)
            cap = pyshark.FileCapture("/".join((self.root, file)), display_filter=self.display_filter)

            # Collect session-ids
            for packet in cap:
                self.results[file].append(packet.diameter.session_id)
                # results = {"filename" : ["sid", "sid", "sid", ...], "filename": [],...}
            self.logger.info("Found %s sessions" % str(len(self.results[file])))
        return

    def collect_sub_ids(self):

        for filename in self.results:
            self.logger.info("Started collect_sub_ids() for %s" % filename)
            self.sub_ids[filename] = []
            cap = pyshark.FileCapture("/".join((self.root, filename)))

            i = 0
            start_time = datetime.datetime.now()
            for packet in cap:
                try:
                    if packet.diameter.session_id in self.results[filename]:
                        sub_id = packet.diameter.e164_msisdn
                        self.sub_ids[filename] = helpers.unique_list(self.sub_ids[filename], sub_id)
                except AttributeError:
                    continue
                i += 1
                if i%1000 == 0:
                    stop_time = datetime.datetime.now()
                    delta = stop_time - start_time
                    processing_speed = str(int(1000/float(delta.seconds)))
                    self.logger.info("1000 packets in %s seconds, %s packet/sec" % (delta.seconds,
                                                                                    processing_speed)
                                     )
                    start_time = datetime.datetime.now()
        return


if __name__ == "__main__":

    prc = Processor("/home/egk/Pile/Work/UPCC/main_kpi")
    prc.find_files()
    prc.collect_diam_sessions()
    prc.collect_sub_ids()

    with open("/home/egk/Pile/Work/UPCC/main_kpi/results.txt", 'w') as f:
        for result_filename in prc.sub_ids:
            f.write(" ".join(prc.sub_ids[result_filename]))

    # prefix = 'e164.msisdn == "'
    # command = prefix + '" or e164.msisdn == "'.join(prc.sub_ids) + '"'
