import json
from pathlib import Path
from collections import OrderedDict
from typing import Dict, Any, Optional

class MetadataSaver:
    """
    Handles sorting, filtering, and saving of Civitai metadata into JSON files.
    """

    def __init__(self, json_path: Path):
        self.json_path = json_path

    def load_existing(self) -> Dict[str, Any]:
        """Load existing JSON if present, else return empty dict."""
        if not self.json_path.exists():
            return {}
        try:
            with self.json_path.open('r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def save(self, data: Dict[str, Any]) -> bool:
        """Save the dict to the JSON file, preserving insertion order."""
        try:
            self.json_path.parent.mkdir(parents=True, exist_ok=True)
            with self.json_path.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except IOError:
            return False

    def filter_initial(self, metadata: Dict[str, Any], sha256: str) -> OrderedDict:
        """
        Build an OrderedDict containing only the desired top-level fields:
        - sha256
        - id
        - modelId
        - trainedWords
        - baseModel
        - model
        """
        out = OrderedDict()
        out['sha256'] = sha256
        for key in ['id', 'modelId', 'trainedWords', 'baseModel', 'model']:
            if key in metadata:
                out[key] = metadata[key]
        return out

    def append_additional(self, data: Dict[str, Any], additional: Dict[str, Any]) -> None:
        """
        Append full additional metadata under a single key at the end.
        e.g. data['additional_metadata'] = additional
        """
        data['additional_metadata'] = additional

    def write_metadata(self,
                       sha256: str,
                       initial_meta: Dict[str, Any],
                       additional_meta: Optional[Dict[str, Any]] = None) -> bool:
        """
        Orchestrate loading, merging, and saving metadata.
        """
        existing = self.load_existing()

        # Filter and order initial metadata
        ordered = self.filter_initial(initial_meta, sha256)

        # Merge any existing fields not overwritten
        merged = {**existing, **ordered}

        # Append additional metadata if provided
        if additional_meta is not None:
            self.append_additional(merged, additional_meta)

        return self.save(merged)

    def fetch_additional_metadata(self, api_client, id: int, model_id: int) -> Dict[str, Any]:
        """
        Placeholder for fetching additional metadata by id and model_id.
        Implement the actual API call when available.
        """
        # Example stub:
        # url = f"{api_client.base_url}/model-versions/{model_id}/metadata"
        # response = api_client._make_request_with_retry(url)
        # if response and response.status_code == 200:
        #     return response.json()
        return {}  # TODO: implement
