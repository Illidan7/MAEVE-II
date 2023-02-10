import sys
import requests

sys.path.append("S://Docs//Personal//MAEVE//Data//Config//")
from config import tg_baseurl

requests.get(tg_baseurl+'"Testing!"')
