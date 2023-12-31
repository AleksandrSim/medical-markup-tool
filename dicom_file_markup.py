import pydicom
import matplotlib.pyplot as plt
import cv2

# Path to your DICOM file
dicom_file_path = '/Users/aleksandrsimonyan/Desktop/george_files/F000001'

# Load the DICOM file
dicom_data = pydicom.dcmread(dicom_file_path)

# Iterate over all DICOM attributes and print them
for tag in dicom_data.dir():
    try:
        value = getattr(dicom_data, tag)
        print(f"{tag}: {value}")
    except AttributeError:
        pass

# Get the pixel array from the DICOM object
image = dicom_data.pixel_array

#qprint(image.shape)

#image = cv2.cvtColor(image, cv2.COLOR_BAYER_GBRG2RGB)

print(image.shape)


# Display the image
plt.imshow(image)
plt.axis('off')  # Turn off axis numbers
plt.show()
