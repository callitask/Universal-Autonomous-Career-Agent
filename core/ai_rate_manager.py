import time
from typing import List

class SmartRateManager:
    """
    Stateful Rate Manager to track Google AI Studio model health.
    Prevents the script from hammering rate-limited models over and over.
    Also ensures global pacing (delays) between Chatbot answers and batch calls.
    """
    def __init__(self):
        self._model_health = {}
        self._last_request_time = 0.0
        # Hard minimum delay (seconds) between ANY API calls (solves Chatbot rapid-fire issue)
        self._min_delay_between_requests = 3.5 
        # If a model hits 429/503, ban it for 2 minutes before trying it again
        self._cooldown_penalty = 120.0 

    def get_available_model(self, model_list: List[str]) -> str:
        current_time = time.time()
        
        # 1. Find the first model in the priority list that is NOT on cooldown
        for model in model_list:
            health = self._model_health.get(model, {"cooldown_until": 0.0})
            if current_time >= health["cooldown_until"]:
                return model
                
        # 2. If ALL models are exhausted, find the one that will unlock the soonest
        soonest_model = min(model_list, key=lambda m: self._model_health.get(m, {}).get("cooldown_until", 0.0))
        wait_time = self._model_health[soonest_model]["cooldown_until"] - current_time
        
        if wait_time > 0:
            print(f"\n[SMART RATE LIMITER] ALERT: All fallback models are exhausted. Sleeping for {wait_time:.1f}s until {soonest_model} cools down...", flush=True)
            time.sleep(wait_time)
            
        return soonest_model

    def report_failure(self, model: str):
        """Places a model in the penalty box after a 429 or 503 error."""
        current_time = time.time()
        self._model_health[model] = {"cooldown_until": current_time + self._cooldown_penalty}
        print(f"[SMART RATE LIMITER] Banned {model} for {self._cooldown_penalty} seconds to recover.", flush=True)

    def enforce_pacing(self):
        """Called right before any API request to enforce minimum time between calls."""
        current_time = time.time()
        elapsed = current_time - self._last_request_time
        if elapsed < self._min_delay_between_requests:
            sleep_time = self._min_delay_between_requests - elapsed
            print(f"[SMART RATE LIMITER] Pacing API traffic. Pausing for {sleep_time:.1f}s...", flush=True)
            time.sleep(sleep_time)
        
        # Record the time the request is actually starting
        self._last_request_time = time.time()

GLOBAL_RATE_MANAGER = SmartRateManager()
