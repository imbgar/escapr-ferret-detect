### Description

Escapr is a tool that helps catch ferrets escaping!

Features:
- Makes use of [Roboflow inference](https://github.com/roboflow/inference/) server to process RTSP feed and execute this workflow:
    - Gather data from RTSP camera feed
    - Generate embedding of both image and prompt text using CLIP model(RN50 variant)
    - Calculates the cosine similarity between the two embeddings.
    - Compares the similarity score with the desired threshold value
    - Outputs `is_match` and `similarity` score.
    - Alert via PagerDuty if an escape is detected.
