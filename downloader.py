import json
import yaml
import os
import xml.etree.ElementTree as ET
import requests
import argparse
import multiprocessing
import subprocess
from tqdm import tqdm
import numpy as np
import time

####################################################################################################
#GLOBAL VARS
####################################################################################################
OPENS_URL="http://catalogue.dataspace.copernicus.eu/resto/api/collections/search.json?"
ODATA_URL="https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
TOKEN_URL="https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"

####################################################################################################
# MAIN CLASS
####################################################################################################
class Downloader:
	"""
	Explanation of the class...
	"""
	def __init__(self):

		#API ACCESS
		self.access_token  = None
		self.refresh_token = None 

		#OBJECT SEARCH PARAMETERS
		self.coord_list = None
		self.parameters = None
		self.query      = None
		self.session    = None


		# params = {
		# 	'coordinates': "",
		# 	'platformname': PLATFORMNAME,
		# 	'producttype': PRODUCT,
		# 	'cloudcoverpercentage': CLOUD_PERCNT,
		# 	'beginPosition': RANGE_TIME,
		# 	'endPosition:': RANGE_TIME,
		# 	'startdate': START_TIME,
		# 	'enddate': STOP_TIME,
		# 	'bands': BAND_RES
		# }


	def set_auth_from_env(self,USER_VAR,PASS_VAR):
		"""
		Set the object's username and password used by the access token to a given environment 
		variable.
		"""
		try:
			self.username = os.getenv(USER_VAR)
		except:
			print("Error setting username to env variable.")
		try:
			self.password = os.getenv(PASS_VAR)
		except:
			print("Error setting passwrod to env variable.")


	def set_access_token(self, username: str, password: str) -> str:
		'''
		The equivalent curl request is:

		curl --location --request POST \
		'https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token' \
		  --header 'Content-Type: application/x-www-form-urlencoded' \
		  --data-urlencode 'grant_type=password' \
		  --data-urlencode 'username=<USERNAME>' \
		  --data-urlencode 'password=<PASSWORD>' \
		  --data-urlencode 'client_id=cdse-public'
		'''

		data = {
	        "client_id":  "cdse-public",
	        "username":   self.username,
	        "password":   self.password,
	        "grant_type": "password",
	    	}

		try:
			r = requests.post(TOKEN_URL,data=data)
			r.raise_for_status()

		except Exception as e:
			raise Exception(
			    f"Keycloak token creation failed. Reponse from the server was: {r.json()}"
			)

		self.access_token  = r.json()["access_token"]
        self.refresh_token = r.json()["refresh_token"]


    def regenerate_access_token(self):
		'''		
		curl --location --request POST \
		'https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token' \
		  --header 'Content-Type: application/x-www-form-urlencoded' \
		  --data-urlencode 'grant_type=<refresh_token>' \
		  --data-urlencode 'refresh_token=<REFRESH_TOKEN>' \
		  --data-urlencode 'client_id=cdse-public'
		''' 
		data = {
			"client_id": "cdse-public",
			"grant_type": "refresh_token",
			"refresh_token": self.refresh_token
		}

		r = requests.post(TOKEN_URL,data=data)
		#CHECK resp content

		self.access_token = None


	def opensearch_uri(self):
		"""
		Uses the parameters currently set in the parameters property of a Downloader object to 
		build an openSearch API query.
		"""
		pass

	"""
	# BASE QUERY
		http://catalogue.dataspace.copernicus.eu/resto/api/collections/search.json?

	# COLLECTIONS
	Collections serve as a way to filter products corresponding to particular satellite.
	For example, the query

		https://catalogue.dataspace.copernicus.eu/resto/api/collections/search.json?
		cloudCover=[0,10]&
		startDate=2022-06-11T00:00:00Z&
		completionDate=2022-06-22T23:59:59Z&
		maxRecords=10"

	returns the most 10 most recent products matching the dates and with less than 10% cloud cover
	in all collections, that is, products from all satellites.

	Instead, the following query will return the ten most recent Sentinel-2 products with less 
	than 10% cloud cover:

		http://catalogue.dataspace.copernicus.eu/resto/api/collections/Sentinel2/search.json?
		cloudCover=[0,10]&
		startDate=2022-06-11T00:00:00Z&
		completionDate=2022-06-22T23:59:59Z&
		maxRecords=10"

	The name of the collections for each satellite are:
		- Sentinel1
		- Sentinel2
		- Sentinel3
		- Sentinel5P

	# SORTING AND LIMITING
	
		http://catalogue.dataspace.copernicus.eu/resto/api/collections/Sentinel2/search.json?
		startDate=2021-07-01T00:00:00Z&
		completionDate=2021-07-31T23:59:59Z&
		sortParam=startDate&
		maxRecords=20


		http://catalogue.dataspace.copernicus.eu/resto/api/collections/Sentinel2/search.json?
		startDate=2021-07-01T00:00:00Z&
		completionDate=2021-07-31T23:59:59Z&
		sortParam=startDate&
		maxRecords=20&
		page=2

		Other parameters are:
			- maxRecords=nnn
			- page=nnn


		Different sortings
		- sortParam=startDate
		- sortParam=completionDate
		- sortParam=published
	
		sortOrder=ascending or sortOrder=descending


	# FORMAL QUERIES
		https://catalogue.dataspace.copernicus.eu/resto/api/collections/Sentinel2/search.json?
		cloudCover=[0,10]&
		startDate=2021-06-21T00:00:00Z&
		completionDate=2021-09-22T23:59:59Z&
		lon=21.01&
		lat=52.22

	# GEOGRAPHY AND TIME-FRAME
	- startDate, completionDate
	- lon,lat:  EPSG:4326 decimal degrees
	- radius:   meters to centre defined by lon and lat.
	- geometry: POINT, POLYGON
	- box: box=west,south,east,north

		https://catalogue.dataspace.copernicus.eu/resto/api/collections/Sentinel2/search.json?
		cloudCover=[0,10]&
		startDate=2022-06-11T00:00:00Z&
		completionDate=2022-06-22T23:59:59Z&
		maxRecords=10&
		box=-1,1,-1,1

		https://catalogue.dataspace.copernicus.eu/resto/api/collections/Sentinel2/search.json?
		cloudCover=[0,10]&
		startDate=2022-06-11T00:00:00Z&
		completionDate=2022-06-22T23:59:59Z&
		maxRecords=10&
		box=-21,23,-24,15

	#SATELLITE FEATURES
	- instrument
	- productType
	- sensorMode
	- orbitDirection
	- resolution
	- status: ONLINE, OFFLINE

	A complete set of query-able parameters for each satellite can be obtained from
		https://catalogue.dataspace.copernicus.eu/resto/api/collections/Sentinel1/describe.xml
		https://catalogue.dataspace.copernicus.eu/resto/api/collections/Sentinel2/describe.xml
		https://catalogue.dataspace.copernicus.eu/resto/api/collections/Sentinel3/describe.xml
		https://catalogue.dataspace.copernicus.eu/resto/api/collections/Sentinel5P/describe.xml	
	"""

	def search(self):
		pass

	def download_product(self):
		pass

	def parse_product_list(self):
		pass


if __name__ == '__main__':

	#SET AUTH FROM ENV OR YAML
	username = os.getenv("DS_USER")
	password = os.getenv("DS_PASS")
	# username =
	# password = 

	D = Downloader()
	D.set_keycloak(username,password)
	pass