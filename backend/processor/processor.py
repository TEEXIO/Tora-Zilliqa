# -*- coding:utf-8 -*-
# Copyright 2019 TEEX
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

from backend.dispatcher.response_dispatcher import ResponseDispatcher
from backend.responder.response import Response
from backend.processor.general_web_api import get_web_api_json_result
from backend.processor.swap_process_register import ZilliqaSwapProcessRegister
from backend.processor.eth_verifier import Verifier
from queue import Queue
import time
import json
import coloredlogs, logging
import threading


class Processor(threading.Thread):

    def __init__(self, configs):
        threading.Thread.__init__(self)

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(int(os.getenv('Tora-log-level')))
        coloredlogs.install(logger=self.logger)

        self.configs = configs

        self.req_q = Queue()
        self.dispatcher = ResponseDispatcher()

    def add_request(self, request):
        self.req_q.put(request)

    def get_request(self):

        if not self.req_q.empty():
            request = self.req_q.get()
            return request
        else:
            return None

    def generate_response_str(self, request, res_str):
        response = Response(request.type, res_str, request.ID, request.chain_name, request.gas_price, request.gas_limit, request.tora_addr, request.user_addr)
        self.dispatcher.dispatch_response(response)

    def process(self, params):
        return

    def run(self):
        while True:

            request = self.get_request()
            if not request:
                time.sleep(1)
            
            else:
                try:
                    param_data = json.loads(request.param.replace("'", '"'))
                    response = self.process(param_data)
                    if response is None:
                        # abort this request
                        continue
                    if not isinstance(response, str):
                        response = str(response)
                except:
                    response = "No correct request params"
                self.generate_response_str(request, response)


class Collector(Processor):

    def process(self, params):
        self.logger.info("Enter Web API Collector~")
        if ('url' not in params.keys()) or ('params' not in params.keys()):
            return "No correct request params"
        result = get_web_api_json_result(params['url'], params['params'])
        return result


class Executor(Processor):
    def process(self, params):
        print("Enter Executor~")
        # TODO:
        return


class SwapRelay(Processor):
    def process(self, params):
        self.logger.info("Enter SwapRelay~")
        print(params)
        swap_id = params['swap_id']
        swap_chain = params['swap_chain']
        initial_chain = params['initial_chain']
        swap_process_register = None
        if initial_chain == "Zilliqa":
            swap_process_register = ZilliqaSwapProcessRegister(self.configs['baseChainContract'])
        if swap_chain == "Ethereum":
            if not swap_process_register:
                if swap_process_register.register_to_process(self.configs['node-sk'], swap_id):
                    tx_hash = params['tx_hash']
                    initial_addr = params['initial_addr']
                    target_addr = params['target_addr']
                    swap_money = params['swap_money']
                    if self.configs["ethereum-provider"] is None:
                        self.logger.info("No ethereum provider set")
                        return None
                    verifier = Verifier(self.configs["ethereum-provider"])
                    result = verifier.verify_transaction(tx_hash, swap_id, initial_addr, target_addr, swap_money)
                    return result
                else:
                    self.logger.info("Process register fail, abort the request")
                    return None
            else:
                self.logger.info("Can't process this chain swap")
                return None
        else:
            self.logger.info("Can't process this chain swap")
            return None


class CrossChainInfoRelay(Processor):

    def process(self, params):
        self.logger.info("Enter CrossChainInfoRelay~")
        print(params)
        if ('contract_addr' not in params.keys()) or ('data_positions' not in params.keys()) \
                or('block_number' not in params.keys()):
            return "No correct request params"
        contract_addr = params['contract_addr']
        data_positions = params['data_positions']
        block_number = params['block_number']

        verifier = Verifier(self.configs["ethereum-provider"])
        result = verifier.verify_state(contract_addr, data_positions, block_number)
        return result
