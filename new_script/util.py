# coding=utf-8

from config import *

import os
import json

class Deploy_Config():
    def __init__(self):
        self.NetWork = []
        self.Relayer = []
        self.Token = []
        self.load()

    def load(self):
        if os.path.exists(deploy_config_path):
            with open(deploy_config_path) as f:
                config_json = json.load(f)   
                self.NetWork = config_json['NetWork']
                self.Relayer = config_json['Relayer']
                self.Token = config_json['Token']

    def save(self):
        with open(deploy_config_path,'w') as f:
            config_json = {'NetWork': self.NetWork, 'Relayer': self.Relayer, 'Token': self.Token}
            json.dump(config_json,f, indent=4)


def load_owner():
    with open(owner_key_path, 'r') as f:
        from web3 import Web3
        owner_acct = Web3().eth.account.from_key(Web3().eth.account.decrypt(f.read(), KEYSTORE_PASSWORD))
        return owner_acct

def focus_print(text):
    print("\n\033[1;36;40m{}\033[0m".format(text)) # 高亮青色前景色换行输出

def sign_send_wait(w3_obj, account_obj, txn):
    signed_txn = account_obj.sign_transaction(txn)
    tx_hash = w3_obj.eth.send_raw_transaction(signed_txn.rawTransaction)
    w3_obj.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash

def Deploy_Contract(w3_obj, json_path, init_args):
    with open(json_path, 'r') as f:
        contract_json = json.load(f)
        abi = contract_json['abi']
        bin = contract_json['bytecode']

    contract = w3_obj.eth.contract(abi=abi, bytecode=bin)
    
    owner_acct = load_owner()

    txn= contract.constructor(*init_args).buildTransaction({'from': owner_acct.address, 'nonce': w3_obj.eth.getTransactionCount(owner_acct.address), "gasPrice": w3_obj.eth.gas_price})
    tx_hash = sign_send_wait(w3_obj, owner_acct, txn)
    tx_receipt = w3_obj.eth.get_transaction_receipt(tx_hash)

    return tx_receipt.contractAddress

def Build_Relayer_Config(config, index=None):
    import random

    Relayer = config.Relayer
    NetWork = config.NetWork
    
    if index:
        Relayer = [config.Relayer[index]]

    for r in Relayer:
        out_json = { "Chains":[] }
        for n in NetWork:
            cur_endpoint = random.choice(n['endpoint'])
            out_json['Chains'].append(
                {
                    "name": n['name'],
                    "type": "ethereum",
                    "id": str(NetWork.index(n)),
                    "endpoint": cur_endpoint,
                    "from": r['address'],
                    "opts": {
                        "bridge": n['bridge'],
                        # "erc20Handler": "",
                        # "erc721Handler": "",
                        "genericHandler": n['handler'],
                        "gasLimit": gasLimit,
                        "maxGasPrice": maxGasPrice,
                        "startBlock": "0",
                        "http": str(not "https://" in cur_endpoint).lower()
                    }
                }
            )
        r_dir = config_dir_path + "/{}".format(r['name'])
        with open(r_dir + "/config.json", 'w') as f:
            json.dump(out_json,f, indent=4)
    
def Build_Relayer_YAML(r_name):
    with open(k8s_template_path, 'r') as f:
        k8s_template = f.read()

    with open(key_dir_path + "/{}_keystore.json".format(r_name), 'r') as f:
        from web3 import Web3
        acct = Web3().eth.account.from_key(Web3().eth.account.decrypt(f.read(), KEYSTORE_PASSWORD))
        privateKey = acct.privateKey.hex()

    k8s_template = k8s_template.replace("{{Key}}", privateKey)
    k8s_template = k8s_template.replace("{{KEYSTORE_PASSWORD}}", KEYSTORE_PASSWORD)
    k8s_template = k8s_template.replace("{{NAME}}", r_name.lower())
    
    r_dir = config_dir_path + "/{}".format(r_name)
    with open(r_dir + "/relayer-deployment.yaml", 'w') as f:
        f.write(k8s_template)