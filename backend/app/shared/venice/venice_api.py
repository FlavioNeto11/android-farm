import os
import base64
from typing import List, Dict, Optional, Union
from openai import OpenAI


class VeniceAPI:
    """Cliente para a API Venice com suporte a visão computacional"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "openai-gpt-4o-mini"):
        self.api_key = api_key or os.getenv("VENICE_API_KEY")
        self.model = model
        self.base_url = "https://api.venice.ai/api/v1"
        
        if not self.api_key:
            raise ValueError("Venice API key is required. Set VENICE_API_KEY environment variable.")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def chat_completion(
        self,
        messages: List[Dict[str, Union[str, Dict]]],
        model: Optional[str] = None,
        response_format: Optional[Dict] = None,
        **kwargs
    ):
        model = model or self.model
        
        return self.client.chat.completions.create(
            model=model,
            messages=messages,
            response_format=response_format,
            **kwargs
        )
    
    def analyze_image(
        self,
        image_data: Union[str, bytes],
        prompt: str,
        model: Optional[str] = None,
        response_format: Optional[Dict] = None
    ):
        if isinstance(image_data, bytes):
            base64_image = base64.b64encode(image_data).decode("utf-8")
        else:
            base64_image = image_data
        
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ]
        
        return self.chat_completion(
            messages=messages,
            model=model,
            response_format=response_format
        )
    
    def check_balance(self):
        return {
            "balance": 10.0,
            "currency": "USD"
        }
