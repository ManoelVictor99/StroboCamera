from pypylon import pylon
import cv2
import numpy as np
import snap7

camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())

EXTERNAL_TRIGGER = True


plc = snap7.client.Client()
# PLC address , Rack e module
plc.connect('172.16.x.x', 0, 2) # 1: plc.connect('172.16.x.x', 0, 2) / 2: plc.connect('172.16.x.x', 0, 2)

aux = True
x = True

print("Aguardando Bobina 1")


while x:
    reading = plc.db_read(40, 42, 1)
    if 1 in reading:
        aux = True
    

    if aux:
        try:
            # setup camera 
            camera.Open()
            camera.Width.Value = camera.Width.Max
            camera.Height.Value = camera.Height.Max

            # set camera to frame trigger mode on Line1
            camera.TriggerSelector.Value = "FrameStart"
            if EXTERNAL_TRIGGER:
                camera.TriggerSource.Value = "Line1"
            else:
                camera.TriggerSource.Value = "Software"
            camera.TriggerMode.Value = "On"

        except Exception as e:
            print(f"Error when configuring the camera: {e}")

        # constant values
        num_images = 4
        screen_width, screen_height = 1366, 768

        # runtime values
        resized_images = []
        current_image_index = 0
        combined_image = np.zeros((screen_height, screen_width, 3), dtype=np.uint8)

        # configure image converter
        converter = pylon.ImageFormatConverter()
        converter.OutputPixelFormat = pylon.PixelType_BGR8packed
        converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

        camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

        while camera.IsGrabbing():
            while current_image_index < num_images:

                cv2.imshow('Combined Images', combined_image)
                key = cv2.waitKey(1)
                if key == 27:  # Esc key to exit
                    camera.StopGrabbing()
                    break
                elif not EXTERNAL_TRIGGER and key == ord(" "):
                    camera.ExecuteSoftwareTrigger()

                if not camera.GetGrabResultWaitObject().Wait(10):
                    continue

                try:
                    # use the context handler, so you dont have to call "grabResult.Release" at the end
                    with camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException) as grabResult:
                        assert grabResult.GrabSucceeded()
                        # Accessing image data
                        image = converter.Convert(grabResult)
                        img = image.GetArray()
                except pylon.TimeoutException as timeout_error:
                    raise AssertionError("Timeout error, this should not happen, "
                                         "because we waited for the image in the wait object before!") from timeout_error

                except AssertionError as assertion_error:
                    raise AssertionError("Unsuccessful grab, this should not happen at all!") from assertion_error

                
                if len(resized_images) < num_images:
                    resized_images.append(img.copy())
                else:
                    resized_images[current_image_index] = img.copy()
                    current_image_index = (current_image_index + 1) % num_images

                for i in range(len(resized_images)):
                    h, w, _ = resized_images[i].shape
                    h_ratio = screen_height // 2
                    w_ratio = screen_width // 2

                    if i == 0:
                        row = 1
                        col = 1
                    elif i == 1:
                        row = 0
                        col = 0
                    elif i == 2:
                        row = 1
                        col = 0
                    elif i == 3:
                        row = 0
                        col = 1

                    resized_images[i] = cv2.resize(resized_images[i], (w_ratio, h_ratio))
                    combined_image[row * h_ratio: (row + 1) * h_ratio, col * w_ratio: (col + 1) * w_ratio, :] = resized_images[i]

        cv2.waitKey(0)
        cv2.destroyAllWindows()
        camera.Close()
        break  
