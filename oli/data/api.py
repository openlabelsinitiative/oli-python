import requests
import yaml

class API:
    def __init__(self, oli_client, api_key: str=None):
        """
        Initialize the DataFetcher with an OLI client.
        
        Args:
            oli_client: The OLI client instance
        """
        self.oli = oli_client
        self.api_url = "https://api.openlabelsinitiative.org"
        self.api_key = api_key

    ### OLI Tags and Value Sets maintained in Github ###

    def get_OLI_tags(self) -> dict:
        """
        Get latest OLI tags from OLI Github repo.
        
        Returns:
            dict: Dictionary of official OLI tags
        """
        url = "https://raw.githubusercontent.com/openlabelsinitiative/OLI/refs/heads/main/1_label_schema/tags/tag_definitions.yml"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                y = yaml.safe_load(response.text)
                y = {i['tag_id']: i for i in y['tags']}
                return y
            else:
                print(f"Failed to fetch OLI tags from Github, are you offline? (or are you not using the latest version of the oli-python package? 'pip install --upgrade oli-python'): {response.status_code}")
        except Exception as e:
            print(f"Failed to fetch OLI tags from Github (are you using the latest version of the oli-python package? 'pip install --upgrade oli-python'): {e}")

    def get_OLI_value_sets(self) -> dict:
        """
        Get latest value sets for OLI tags.
        
        Returns:
            dict: Dictionary of value sets with tag_id as key
        """
        value_sets = {}

        # Extract value sets from tag definitions (must be a list)
        for tag_def in self.oli.tag_definitions.values():
            if 'schema' not in tag_def:
                continue
            
            schema = tag_def['schema']
            tag_id = tag_def['tag_id']
            value_set = None
            
            # Get enum from direct schema or array items
            if 'enum' in schema:
                value_set = schema['enum']
            elif (schema.get('type') == 'array' and 
                'items' in schema and 
                'enum' in schema['items']):
                value_set = schema['items']['enum']
            
            # Process and add to value_sets
            if value_set and isinstance(value_set, list):
                value_sets[tag_id] = [i.lower() if isinstance(i, str) else i for i in value_set]

        # value set for owner_project
        url = "https://api.growthepie.com/v1/labels/projects.json" 
        try:
            response = requests.get(url)
            if response.status_code == 200:
                y = yaml.safe_load(response.text)
                value_sets["owner_project"] = [i[0] for i in y['data']['data']]
                value_sets["owner_project"] = [i.lower() if isinstance(i, str) else i for i in value_sets["owner_project"]]
            else:
                print(f"Failed to fetch owner_project value set from growthepie projects api, are you offline? (or are you not using the latest version of the oli-python package? 'pip install --upgrade oli-python'): {response.status_code}")
        except Exception as e:
            print(f"Failed to fetch owner_project value set from growthepie projects api (are you using the latest version of the oli-python package? 'pip install --upgrade oli-python'): {e}")

        # value set for usage_category
        url = "https://raw.githubusercontent.com/openlabelsinitiative/OLI/refs/heads/main/1_label_schema/tags/valuesets/usage_category.yml"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                y = yaml.safe_load(response.text)
                value_sets['usage_category'] = [i['category_id'] for i in y['categories']]
                value_sets['usage_category'] = [i.lower() if isinstance(i, str) else i for i in value_sets['usage_category']]
            else:
                print(f"Failed to fetch usage_category value set from OLI Github, are you offline? (or are you not using the latest version of the oli-python package? 'pip install --upgrade oli-python'): {response.status_code}")
        except Exception as e:
            print(f"Failed to fetch usage_category value set from OLI Github (are you using the latest version of the oli-python package? 'pip install --upgrade oli-python'): {e}")

        return value_sets

    ### Parquet exports of OLI Label Pool by growthepie ###

    def get_full_raw_export_parquet(self, file_path: str="raw_labels.parquet") -> str:
        """
        Downloads the full raw export of all labels in the OLI Label Pool as a Parquet file.
        
        Args:
            file_path (str): Path where the file will be saved. Defaults to "raw_labels.parquet".
            
        Returns:
            str: Path to the downloaded Parquet file
        """
        url = "https://api.growthepie.com/v1/oli/labels_raw.parquet"
        
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(file_path, 'wb') as f:
                f.write(response.content)
            print(f"Downloaded and saved: {file_path}")
            return file_path
        else:
            print(f"Failed to download {url}. Status code: {response.status_code}")
            return None

    def get_full_decoded_export_parquet(self, file_path: str="decoded_labels.parquet") -> str:
        """
        Downloads the full decoded export of all labels in the OLI Label Pool as a Parquet file.
        
        Args:
            file_path (str): Path where the file will be saved. Defaults to "decoded_labels.parquet".
            
        Returns:
            str: Path to the downloaded Parquet file
        """
        url = "https://api.growthepie.com/v1/oli/labels_decoded.parquet"
        
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(file_path, 'wb') as f:
                f.write(response.content)
            print(f"Downloaded and saved: {file_path}")
            return file_path
        else:
            print(f"Failed to download {url}. Status code: {response.status_code}")
            return None
        
    ### OLI API ENDPOINTS ###

    def post_single_attestation(self, attestation: dict) -> dict:
        """
        Post a single attestation to the OLI Label Pool.
        
        Args:
            attestation (dict): The attestation object containing sig and signer
            
        Returns:
            dict: Response with uid and status (e.g., {"uid": "string", "status": "queued"})
        """
        url = f"{self.api_url}/attestation"
        response = requests.post(url, json=attestation)
        if response.status_code == 200:
            return response
        else:
            raise Exception(f"Failed to post single attestation: {response.status_code} - {response.text}")
    
    def post_bulk_attestations(self, attestations: list) -> dict:
        """
        Post multiple attestations to the OLI Label Pool in bulk.
        
        Args:
            attestations (list): List of attestation objects (1-1000 items)
            
        Returns:
            dict: Response with accepted count, duplicates, failed_validation, and status
        """
        url = f"{self.api_url}/attestations/bulk"
        
        if not 1 <= len(attestations) <= 1000:
            raise ValueError("attestations must contain between 1 and 1000 items")
        
        payload = {"attestations": attestations}
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return response
        else:
            raise Exception(f"Failed to post bulk attestations: {response.status_code} - {response.text}")
    
    def get_attestations(self, uid: str = None, attester: str = None, recipient: str = None, schema_info: str = None, since: str = None, order: str = "desc", limit: int = 1000) -> dict:
        """
        Get raw attestations from storage with optional filters.
        
        Args:
            uid (str): Filter by specific attestation UID (0x...). If provided, other filters are ignored
            attester (str): Filter by attester address (0x...)
            recipient (str): Filter by recipient address (0x...)
            schema_info (str): Filter by schema_info (e.g. '8453__0xabc...')
            since (str): Return only attestations created after this timestamp (ISO8601 or Unix seconds)
            order (str): Order results by attestation time ('asc' or 'desc'). Default: 'desc'
            limit (int): Max number of attestations to return (1-1000). Default: 1000
            
        Returns:
            dict: Response with count and attestations array
        """
        url = f"{self.api_url}/attestations"
        
        params = {}
        if uid:
            params['uid'] = uid
        if attester:
            params['attester'] = attester
        if recipient:
            params['recipient'] = recipient
        if schema_info:
            params['schema_info'] = schema_info
        if since:
            params['since'] = since
        if order:
            params['order'] = order
        if limit:
            params['limit'] = limit
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get attestations: {response.status_code} - {response.text}")
    
    def post_trust_list(self, trust_list: dict) -> dict:
        """
        Post a trust list to the OLI Label Pool.
        
        Args:
            trust_list (dict): The trust list object
            
        Returns:
            dict: Response with uid and status (e.g., {"uid": "string", "status": "queued"})
        """
        url = f"{self.api_url}/trust-list"
        response = requests.post(url, json=trust_list)
        if response.status_code == 200:
            return response
        else:
            raise Exception(f"Failed to post trust list: {response.status_code} - {response.text}")

    def get_trust_lists(self, uid: str = None, attester: str = None, order: str = "desc", limit: int = 1000) -> dict:
        """
        Get trust lists with optional filters.
        
        Args:
            uid (str): Filter by specific trust list UID (0x...)
            attester (str): Filter by attester address (0x...)
            order (str): Order by time ('asc' or 'desc'). Default: 'desc'
            limit (int): Max number of rows to return (1-1000). Default: 1000
            
        Returns:
            dict: Response with count and trust_lists array
        """
        url = f"{self.api_url}/trust-lists"
        
        params = {}
        if uid:
            params['uid'] = uid
        if attester:
            params['attester'] = attester
        if order:
            params['order'] = order
        if limit:
            params['limit'] = limit
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get trust lists: {response.status_code} - {response.text}")

    def get_labels(self, address: str, chain_id: str = None, limit: int = 100, include_all: bool = False) -> dict:
        """
        Get labels (key/value) for a given address. Requires API key authentication.
        By default, returns only the newest label per (chain_id, attester, tag_id).
        
        Args:
            address (str): Address (0x...) [required]
            chain_id (str): Optional chain_id filter (e.g., 'eip155:8453')
            limit (int): Max number of labels to return (<=1000). Default: 100
            include_all (bool): If False (default), return only the latest label per (chain_id, attester, tag_id)
            
        Returns:
            dict: Response with address, count, and labels array
            
        Raises:
            ValueError: If api_key is not provided
        """
        if not self.api_key:
            raise ValueError(
                "API key is required for this endpoint. This is a protected endpoint that requires authentication.\n"
                "Protected endpoints: get_labels, get_labels_bulk, search_addresses_by_tag, get_attester_analytics\n"
                "Please provide an api_key parameter when calling this method.\n"
                "You can obtain a free API key at https://openlabelsinitiative.org/signup"
            )
        
        url = f"{self.api_url}/labels"
        
        headers = {'X-API-Key': self.api_key}
        
        params = {'address': address}
        if chain_id:
            params['chain_id'] = chain_id
        if limit:
            params['limit'] = limit
        if include_all is not None:
            params['include_all'] = include_all
        
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get labels: {response.status_code} - {response.text}")
    
    def get_labels_bulk(self, addresses: list, chain_id: str = None, limit_per_address: int = 1000, include_all: bool = False) -> dict:
        """
        Get labels for multiple addresses in bulk. Requires API key authentication.
        
        Args:
            addresses (list): List of addresses (1-100 items) [required]
            chain_id (str): Optional chain_id filter (e.g., 'eip155:8453')
            limit_per_address (int): Max labels to return per address (1-1000). Default: 1000
            include_all (bool): Include all labels vs only latest per (chain_id, attester, tag_id). Default: False
            
        Returns:
            dict: Response with results array containing address and labels for each address
            
        Raises:
            ValueError: If api_key is not provided or if addresses list is invalid
        """
        if not self.api_key:
            raise ValueError(
                "API key is required for this endpoint. This is a protected endpoint that requires authentication.\n"
                "Protected endpoints: get_labels, get_labels_bulk, search_addresses_by_tag, get_attester_analytics\n"
                "Please provide an api_key parameter when calling this method.\n"
                "You can obtain a free API key at https://openlabelsinitiative.org/signup"
            )
        
        url = f"{self.api_url}/labels/bulk"
        
        if not 1 <= len(addresses) <= 100:
            raise ValueError("addresses must contain between 1 and 100 items")
        
        headers = {'X-API-Key': self.api_key}
        
        payload = {
            "addresses": addresses,
            "limit_per_address": limit_per_address,
            "include_all": include_all
        }
        if chain_id:
            payload['chain_id'] = chain_id
        
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get labels bulk: {response.status_code} - {response.text}")
    
    def search_addresses_by_tag(self, tag_id: str, tag_value: str, chain_id: str = None, limit: int = 1000) -> dict:
        """
        Search for all addresses that have a specific tag_id=tag_value pair. Requires API key authentication.
        
        Args:
            tag_id (str): The tag key (e.g., 'usage_category') [required]
            tag_value (str): The tag value (e.g., 'dex') [required]
            chain_id (str): Optional chain_id filter (e.g., 'eip155:8453')
            limit (int): Max number of addresses to return (1-1000). Default: 1000
            
        Returns:
            dict: Response with tag_id, tag_value, count, and results array
            
        Raises:
            ValueError: If api_key is not provided
        """
        if not self.api_key:
            raise ValueError(
                "API key is required for this endpoint. This is a protected endpoint that requires authentication.\n"
                "Protected endpoints: get_labels, get_labels_bulk, search_addresses_by_tag, get_attester_analytics\n"
                "Please provide an api_key parameter when calling this method.\n"
                "You can obtain a free API key at https://openlabelsinitiative.org/signup"
            )
        
        url = f"{self.api_url}/addresses/search"
        
        headers = {'X-API-Key': self.api_key}
        
        params = {
            'tag_id': tag_id,
            'tag_value': tag_value
        }
        if chain_id:
            params['chain_id'] = chain_id
        if limit:
            params['limit'] = limit
        
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to search addresses by tag: {response.status_code} - {response.text}")
    
    def get_attester_analytics(self, chain_id: str = None, limit: int = 100) -> dict:
        """
        Get analytics summary grouped by attester. Requires API key authentication.
        Returns count of labels and unique attestations per attester.
        
        Args:
            chain_id (str): Optional chain_id filter (e.g., 'eip155:8453')
            limit (int): Number of rows to return (1-100). Default: 100
            
        Returns:
            dict: Response with count and results array containing attester, label_count, and unique_attestations
            
        Raises:
            ValueError: If api_key is not provided
        """
        if not self.api_key:
            raise ValueError(
                "API key is required for this endpoint. This is a protected endpoint that requires authentication.\n"
                "Protected endpoints: get_labels, get_labels_bulk, search_addresses_by_tag, get_attester_analytics\n"
                "Please provide an api_key parameter when calling this method.\n"
                "You can obtain a free API key at https://openlabelsinitiative.org/signup"
            )
        
        url = f"{self.api_url}/analytics/attesters"
        
        headers = {'X-API-Key': self.api_key}
        
        params = {}
        if chain_id:
            params['chain_id'] = chain_id
        if limit:
            params['limit'] = limit
        
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get attester analytics: {response.status_code} - {response.text}")