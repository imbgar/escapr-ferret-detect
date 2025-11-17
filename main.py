"""Ferret escape prevention using an RTSP camera feed and an inference server."""
from inference_sdk import InferenceHTTPClient
from typing import Dict, Any, Optional
import time
import requests


class FerretDetector():
  """A class to detect ferrets escaping using an RTSP camera feed and an inference server."""
  
  def __init__(self,
        rtsp_url: str,
        api_url: str = "http://localhost:9001",
        max_fps: int = 4,
        prompt: str = "ferret",
        threshold: float = 0.16,
        workspace_name: str = "local",
        workflow_id: str = "clip-frames"):
    """Initialize the FerretDetector with API URL, max FPS, and RTSP URL and other basic configurations."""
    
    if not rtsp_url:
        raise ValueError("RTSP URL cannot be empty")
    
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("Threshold must be between 0.0 and 1.0")
    
    self.rtsp_url = rtsp_url
    self.api_url = api_url
    self.max_fps = max_fps
    self.prompt = prompt
    self.threshold = threshold
    self.workspace_name = workspace_name
    self.workflow_id = workflow_id
    self._pipeline_id: str = ""

    self._client = InferenceHTTPClient(api_url=self.api_url, api_key="")

  @property
  def pipeline_id(self) -> str:
    """Get the current pipeline ID."""
    return self._pipeline_id
    
  @property
  def is_running(self) -> bool:
    """Check if the pipeline is running."""
    return self._pipeline_id != ""
    
  def start(self, max_fps: Optional[int] = None):
    """Start the inference pipeline with the specified parameters."""
    if self.is_running:
      raise RuntimeError("Pipeline is already running")
    
    fps = max_fps if max_fps is not None else self.max_fps
  
    result: Dict[str, Any] = self._client.start_inference_pipeline_with_workflow(
        video_reference=[self.rtsp_url],
        workspace_name=self.workspace_name,
        workflow_id=self.workflow_id,
        max_fps=fps,
        workflows_parameters={
            "prompt": self.prompt,
            "threshold": self.threshold,
        }
    )
    
    self._pipeline_id = result["context"]["pipeline_id"]

  def stop(self) -> None:
    """Stop the inference pipeline."""
    if self._pipeline_id:
        self._client.terminate_inference_pipeline(self._pipeline_id)
        self._pipeline_id = ""

  def consume(self):
    """Consume the inference pipeline results."""
    
    print("starting to consume results...")
    confidence: float = 0
    confidence_elapsed: float = 0

    while True:
        result = self._client.consume_inference_pipeline_result(pipeline_id=self._pipeline_id)

        if not result["outputs"] or not result["outputs"][0]:
          continue

        output = result["outputs"][0]
        is_match = output.get("is_match")
        similarity = round(output.get("similarity")*100, 1)
        if is_match:
            print(f"!!! FERRET DETECTED !!! - Similarity: {similarity}%")
            confidence += 1
        else:
            print(f"No ferret detected - Similarity: {similarity}%")
        
        if confidence >= 15:
            print("Paging responders..")
            result = self.create_pagerduty_incident(
                summary="Ferret has escaped!!!",
                severity="critical",
                source="Front yard camera"
            )

            print(result)

            confidence = 0

        # reset confidence every 10 seconds
        if confidence_elapsed >= 10:
            confidence = 0
        confidence_elapsed += (1/self.max_fps)

        time.sleep(1/self.max_fps)
    
  def create_pagerduty_incident(self,
                                summary: str,
                                severity: str = "critical",
                                source: str = "Front yard camera",
                                routing_key: str = "") -> Dict[str, Any]:
    url = "https://events.pagerduty.com/v2/enqueue"
    
    payload = {
        "payload": {
            "summary": summary,
            "severity": severity,
            "source": source
        },
        "routing_key": routing_key,
        "event_action": "trigger"
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    
    return response.json()

  def __enter__(self):
    """Context manager entry."""
    self.start()
    print("Initializing ferret detection...")
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    """Context manager exit."""
    print("Stopping ferret detection...")
    self.stop()
    print("Ferret detection stopped...")

def main(config: Dict[str, Any] = {}) -> int:
    """End to end execution workflow

    Example config and usage:
    config = {
        "rtsp_url": "rtsp://user:password@127.0.0.1/live",
        "api_url": "http://localhost:9001",
        "max_fps": 4,
        "threshold": 0.16
    }

    >>> main(config)
    """
    try:
      with FerretDetector(**config) as detector:
        print(f"Starting ferret detection on {config['rtsp_url']}")
        print(f"Processing at {config['max_fps']} FPS with threshold {config['threshold']}")
        print("Pipeline ID:", detector.pipeline_id)
        print("Press Ctrl+C to stop...\n")
                
        detector.consume()
    except KeyboardInterrupt:
        print("\nShutdown complete.")
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    main(config = {
        "rtsp_url": "rtsp://ferretcam:escape@192.168.1.36/live",
        "api_url": "http://localhost:9001",
        "max_fps": 4,
        "threshold": 0.16
})