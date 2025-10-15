# API


### Search pattenrn in an image

``` python
    from hope_documents.ocr.engine import SEARCH_TEST_PATTERN, CV2Config, MatchMode, Processor, SearchInfo, TSConfig

    ts_config = TSConfig(psm=11, oem=3)
    cv2_config = CV2Config()

    processor = Processor(ts_config, cv2_config)
    si: SearchInfo
    for si in processor.find_text("my_image.png", "pattern"):
        if si.match:
            print("Text found in image. Distance is:", si.match.distance)
        else:
            print("Text not found")

```
