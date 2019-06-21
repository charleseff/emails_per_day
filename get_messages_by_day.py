#!/usr/bin/env python3

from __future__ import print_function

import math
import pickle
import os.path
import pprint

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import datetime

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


class GetMessagesByDay():
    def set_service(self):
        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
            # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server()
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        self.service = build('gmail', 'v1', credentials=creds)

    def run(self):
        self.set_service()

        print("Getting message count by day in my inbox:")

        self.dates_by_msg_index = []
        self.index_of_first_message_for_last_date = 0

        counts_by_date = []
        today = datetime.datetime.now().date()

        messages_result = self.service.users().messages().list(userId='me', labelIds=['INBOX'],
                                                               maxResults=500).execute()
        self.all_messages = messages_result['messages']
        self.next_page_token = messages_result['nextPageToken']

        self.set_date_for_index(0)
        self.set_date_for_index(len(self.all_messages) - 1)

        # last 100 days: (switch to 100)
        for days_back in range(100):
            date = today - datetime.timedelta(days=(days_back + 1))
            index_of_first_message_for_date = self.get_index_of_first_message_for_date(date)
            number_of_messages = index_of_first_message_for_date - self.index_of_first_message_for_last_date
            counts_by_date.append((date, number_of_messages))
            self.index_of_first_message_for_last_date = index_of_first_message_for_date
            # sort:
            self.dates_by_msg_index = sorted(self.dates_by_msg_index, key=lambda val: val[0])

            print("Got index %s for %s, for %s total messages" % (
            index_of_first_message_for_date, date, number_of_messages))

        counts_with_date = [[str(x[0]), x[1]] for x in counts_by_date]
        print("Counts by date: ")
        pprint.PrettyPrinter(indent=4).pprint(counts_with_date)

        # print(self.dates_by_index.queue)
        # pdb.set_trace()

    # returns date
    def set_date_for_index(self, index):
        message = self.service.users().messages().get(userId='me', id=self.all_messages[index]['id']).execute()
        date_of_message = datetime.datetime.fromtimestamp(int(message['internalDate']) / 1000).date()
        self.dates_by_msg_index.append((index, date_of_message))
        return date_of_message

    def get_index_of_first_message_for_date(self, date):
        index, (prior_message_index, _date_at_pointer) = next(
            (i, v) for i, v in enumerate(self.dates_by_msg_index) if v[0] == self.index_of_first_message_for_last_date)

        while (True):
            message_index, date_at_pointer = self.dates_by_msg_index[index]

            if date_at_pointer > date:
                if len(self.dates_by_msg_index) - 1 == index:
                    messages_result = self.service.users().messages().list(userId='me', labelIds=['INBOX'],
                                                                           maxResults=500,
                                                                           pageToken=self.next_page_token).execute()
                    self.all_messages += messages_result['messages']
                    self.next_page_token = messages_result['nextPageToken']

                    self.set_date_for_index(len(self.all_messages) - 1)
                index += 1
                prior_message_index = message_index
            else:
                # binary search to find the index of first message for date:
                print("The first message index for date %s is somewhere between %s and %s, going to binary search" % (
                    date, prior_message_index, message_index))
                message_index = self.binary_search_get_index_of_first_message_for_date(date, prior_message_index,
                                                                                       message_index)
                break

        return message_index

    def binary_search_get_index_of_first_message_for_date(self, date, prior_message_index, message_index):
        upper = message_index
        lower = prior_message_index

        if upper == lower:
            return upper
        while (True):
            if upper - lower == 1:
                return upper
            message_index_to_try = math.floor((upper + lower) / 2)
            date_of_message = self.set_date_for_index(message_index_to_try)
            # print("Date of message at index %s = %s" % (message_index_to_try, date_of_message))
            if date_of_message > date:
                lower = message_index_to_try
            else:
                upper = message_index_to_try


if __name__ == '__main__':
    GetMessagesByDay().run()
