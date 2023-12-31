import argparse
import tkinter as tk
from PIL import Image, ImageTk
import cv2
import glob
import json
import os
import numpy as np

class ImageAnnotationApp:
    def __init__(self, window, window_title, input_folder, output_folder):
        self.window = window
        self.current_corner = None
        window.bind('<w>', self.set_top_left)
        window.bind('<e>', self.set_bottom_right)
        window.bind('<r>', self.reset)
        self.current_image_name = None
        window.bind('<d>', self.delete_latest_annotation)
        window.bind('<i>', self.draw_vertical_lines_to_segment)

        self.window.title(window_title)
        sizes = [500,500]
        self.R = 1
        self.input_folder = input_folder
        self.output_folder = output_folder
        self.annotations = {}
        self.current_annotation_class = 1
        self.image_paths = glob.glob(f'{input_folder}/*.jpg')
        self.current_image_index = 0
        self.annotations_temp = []
        self.photo = None

        # Initialize canvas before loading images
        self.canvas = tk.Canvas(window, width=sizes[0], height=sizes[1])
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.zoom_center = (sizes[0] / 2, sizes[1] / 2)  # Center of the canvas
        self.zoom_level = 1

        # UI components
        self.create_navigation_buttons()
        self.create_scale()
        self.create_class_switch_buttons()
        self.image_name_label = tk.Label(window, text="")
        self.image_name_label.pack()

        # Key bindings
        window.bind('<Left>', lambda event: self.prev_image())
        window.bind('<Right>', lambda event: self.next_image())
        window.bind('<q>', lambda event: self.close_app())
        window.bind('1', lambda event: self.set_annotation_class(1))
        window.bind('2', lambda event: self.set_annotation_class(2))
        window.bind('=', lambda event: self.change_zoom(1.1))  # Zoom in
        window.bind('-', lambda event: self.change_zoom(0.9)) 
        self.zoom_level = 1

        # Load existing annotations and the first image
        self.load_existing_annotations()
        if self.image_paths:
            self.load_image(0)  # Load the first image
        self.window.mainloop()

    def draw_vertical_lines_to_segment(self, event):
        blue_points = [ann['point'] for ann in self.annotations_temp if ann['class'] == 'blue']
        red_points = [ann['point'] for ann in self.annotations_temp if ann['class'] == 'red']
        red_segments = [(red_points[i], red_points[i+1]) for i in range(len(red_points)-1)]

        for bp in blue_points:
            for segment in red_segments:
                if self.is_x_within_segment(bp[0], segment):
                    y_on_segment = self.get_y_on_segment(bp[0], segment)
                    if y_on_segment is not None:
                        self.canvas.create_line(bp[0], bp[1], bp[0], y_on_segment, fill="purple")

    def is_x_within_segment(self, x, segment):
        x1, _ = segment[0]
        x2, _ = segment[1]
        return min(x1, x2) <= x <= max(x1, x2)

    def get_y_on_segment(self, x, segment):
        (x1, y1), (x2, y2) = segment
        if x1 == x2:  # Vertical segment
            return min(y1, y2) if min(y1, y2) <= x <= max(y1, y2) else None
        # Linear interpolation for non-vertical segment
        return y1 + (y2 - y1) * (x - x1) / (x2 - x1)
    
    def delete_latest_annotation(self, event):
        # Check if there are any annotations to delete
        if self.annotations_temp:
            self.annotations_temp.pop()  # Remove the last annotation
            self.draw_annotations()  # 

    def check_bbox(self):
        if 'top_left' and 'bottom_right' in self.annotations[self.current_image_name]:
            self.draw_annotations()

    def check_image(self):
        self.current_image_name = os.path.basename(self.image_paths[self.current_image_index])
        if self.current_image_name not in self.annotations:
            self.annotations[self.current_image_name]= {}

    def set_top_left(self, event):
        self.check_image()

        self.top_left_coords = [event.x, event.y]
        if 'top_left' in self.annotations[self.current_image_name]:
                del self.annotations[self.current_image_name]['top_left']
        self.annotations[self.current_image_name]['top_left'] = self.top_left_coords 
        self.check_bbox()


    def set_bottom_right(self, event):
        self.check_image()

        self.bottom_right_coords = [event.x, event.y]
        if 'bottom_right' in self.annotations[self.current_image_name]:
                del self.annotations[self.current_image_name]['bottom_right']
        self.annotations[self.current_image_name]['bottom_right'] = self.bottom_right_coords
        self.check_bbox()

    def reset(self, event):
        self.current_corner = None

    def change_zoom(self, factor):
        self.zoom_level *= factor
        self.zoom_level = max(1, self.zoom_level)  # Prevent zooming out beyond original size
        self.update_image_for_zoom()

    def update_image_for_zoom(self):
        if self.image:
            width, height = self.image.width, self.image.height
            new_size = (int(width * self.zoom_level), int(height * self.zoom_level))
            resized_image = self.image.resize(new_size)

            self.photo = ImageTk.PhotoImage(resized_image)
            self.display_image()

    def load_existing_annotations(self):
        annotation_file = os.path.join(self.output_folder, 'annotations.json')
        if os.path.exists(annotation_file):
            with open(annotation_file, 'r') as infile:
                self.annotations = json.load(infile)
            current_image_name = os.path.basename(self.image_paths[self.current_image_index])
            if current_image_name in self.annotations:
                self.annotations_temp = self.annotations[current_image_name]
                self.draw_annotations()

    def draw_annotations(self):
        # Clear the canvas, but only if a new image is loaded
        if self.photo is not None:
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)

        if self.annotations_temp:
            for i, annotation in enumerate(self.annotations_temp):
                # Check if the annotation is in the expected dictionary format
                if isinstance(annotation, dict) and 'point' in annotation and 'class' in annotation:
                    original_x, original_y = annotation['point']
                    color = annotation['class']  # Use the color associated with the annotation

                    # Convert to zoomed coordinates for display
                    x = (original_x * self.zoom_level) + (self.zoom_center[0] * (1 - self.zoom_level))
                    y = (original_y * self.zoom_level) + (self.zoom_center[1] * (1 - self.zoom_level))
                else:
                    # Skip the iteration if the format is unrecognized
                    continue

                self.canvas.create_oval(x - self.R, y - self.R, x + self.R, y + self.R, fill=color)

                if i > 0:
                    prev_annotation = self.annotations_temp[i - 1]
                    if isinstance(prev_annotation, dict) and 'point' in prev_annotation and 'class' in prev_annotation:
                        prev_original_x, prev_original_y = prev_annotation['point']
                        prev_color = prev_annotation['class']
                        prev_x = (prev_original_x * self.zoom_level) + (self.zoom_center[0] * (1 - self.zoom_level))
                        prev_y = (prev_original_y * self.zoom_level) + (self.zoom_center[1] * (1 - self.zoom_level))

                    # Draw line if the previous annotation color matches the current one
                    if prev_color == color:
                        self.canvas.create_line(prev_x, prev_y, x, y, fill=color)

        if self.current_image_name in self.annotations:

            if 'top_left' in self.annotations[self.current_image_name] and 'bottom_right' in self.annotations[self.current_image_name]:
                        # Draw bounding boxes
                        top_left_x, top_left_y = self.annotations[self.current_image_name]['top_left']
                        bottom_right_x, bottom_right_y = self.annotations[self.current_image_name]['bottom_right']

                        # Convert to zoomed coordinates for display
                        tl_x = (top_left_x * self.zoom_level) + (self.zoom_center[0] * (1 - self.zoom_level))
                        tl_y = (top_left_y * self.zoom_level) + (self.zoom_center[1] * (1 - self.zoom_level))
                        br_x = (bottom_right_x * self.zoom_level) + (self.zoom_center[0] * (1 - self.zoom_level))
                        br_y = (bottom_right_y * self.zoom_level) + (self.zoom_center[1] * (1 - self.zoom_level))

                        self.canvas.create_rectangle(tl_x, tl_y, br_x, br_y, outline="green")


    def create_class_switch_buttons(self):
        self.class_label = tk.Label(self.window, text="Current Class: Red")
        self.class_label.pack(side=tk.TOP)

        self.btn_class_red = tk.Button(self.window, text="Red Class", command=lambda: self.set_annotation_class(1))
        self.btn_class_red.pack(side=tk.LEFT)

        self.btn_class_blue = tk.Button(self.window, text="Blue Class", command=lambda: self.set_annotation_class(2))
        self.btn_class_blue.pack(side=tk.LEFT)
        
    def set_annotation_class(self, annotation_class):
        self.current_annotation_class = annotation_class
        class_name = "Red" if annotation_class == 1 else "Blue"
        self.class_label.config(text=f"Current Class: {class_name}")

    # No need to call draw_annotations here unless you want to redraw existing points
    def create_navigation_buttons(self):
        self.btn_prev = tk.Button(self.window, text="Previous", command=self.prev_image)
        self.btn_prev.pack(side=tk.LEFT)

        self.btn_next = tk.Button(self.window, text="Next", command=self.next_image)
        self.btn_next.pack(side=tk.RIGHT, anchor=tk.NE)

        self.btn_save = tk.Button(self.window, text="Save Annotations", command=self.save_annotations)
        self.btn_save.pack(side=tk.BOTTOM)

    def create_scale(self):
        self.scale_value = tk.IntVar()
        self.scale = tk.Scale(self.window, from_=0, to=len(self.image_paths) - 1, orient="horizontal", variable=self.scale_value, command=self.on_scale)
        self.scale.pack()

    def on_scale(self, val):
        index = int(float(val))
        if index != self.current_image_index:
            self.save_current_annotations()
            self.load_image(index)  # Pass the new index to load_image
                
    def on_canvas_click(self, event):

        original_x = (event.x - self.zoom_center[0]) / self.zoom_level + self.zoom_center[0]
        original_y = (event.y - self.zoom_center[1]) / self.zoom_level + self.zoom_center[1]
        self.current_image_name = os.path.basename(self.image_paths[self.current_image_index])

        if not self.current_corner:
            annotation_class = 'blue' if self.current_annotation_class == 2 else 'red'
            new_annotation = {'point': (original_x, original_y), 'class': annotation_class}
            self.annotations_temp.append(new_annotation)
        self.draw_annotations()

    def close_app(self, event=None):
        self.save_current_annotations()  # Save annotations for the current image
        self.save_annotations()  # Save all annotations to the file
        self.window.destroy()

    def load_image(self, index):
        if 0 <= index < len(self.image_paths):
            # Load the new image
            self.cv_image = cv2.cvtColor(cv2.imread(self.image_paths[index]), cv2.COLOR_BGR2RGB)
            self.image = Image.fromarray(self.cv_image)
            self.photo = ImageTk.PhotoImage(self.image)
            self.current_image_index = index

            self.update_canvas_size()
            self.update_image_name_label()

            self.canvas.delete("all")
            self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)
            self.load_annotations_for_current_image()
            self.draw_annotations()
            self.window.update_idletasks()  #
            
    def load_annotations_for_current_image(self):
        current_image_name = os.path.basename(self.image_paths[self.current_image_index])
        if current_image_name in self.annotations:
            annotations_for_image = self.annotations[current_image_name]
            # Combine red and blue annotations
            self.annotations_temp = annotations_for_image.get('red', []) + annotations_for_image.get('blue', [])
        else:
            self.annotations_temp = []
        self.draw_annotations()  # This should visualize annotations immediately


    def update_canvas_size(self):
        self.canvas.config(width=self.image.width, height=self.image.height)

    def display_image(self):
        self.canvas.delete("all")
        # Adjust image position based on zoom center
        x = self.zoom_center[0] * (1 - self.zoom_level)
        y = self.zoom_center[1] * (1 - self.zoom_level)
        self.canvas.create_image(x, y, image=self.photo, anchor=tk.NW)
        self.draw_annotations()

    # Removed self.canvas.lift() as it's not needed
    def next_image(self):
        if self.current_image_index < len(self.image_paths) - 1:
            self.save_current_annotations()
            self.load_image(self.current_image_index + 1)

    def prev_image(self):
        if self.current_image_index > 0:
            self.save_current_annotations()
            self.load_image(self.current_image_index - 1)

    def update_image_name_label(self):
        self.current_image_name = os.path.basename(self.image_paths[self.current_image_index])
        self.image_name_label.config(text=f"Current Image: {self.current_image_name}")


    def draw_point(self, x, y):
        r = 5
        self.canvas.create_oval(x - r, y - r, x + r, y + r, fill="red")

    def save_current_annotations(self):
        self.current_image_name = os.path.basename(self.image_paths[self.current_image_index])
        if self.current_image_name not in self.annotations:
            self.annotations[self.current_image_name] = {'red': [], 'blue': []}

        # Clear existing annotations for the current image before saving
        self.annotations[self.current_image_name]['red'].clear()
        self.annotations[self.current_image_name]['blue'].clear()

        for annotation in self.annotations_temp:
            if isinstance(annotation, dict) and 'class' in annotation and 'point' in annotation:
                annotation_class = annotation['class']
                self.annotations[self.current_image_name][annotation_class].append(annotation)

    def save_annotations(self):
        with open(os.path.join(self.output_folder, 'annotations.json'), 'w') as outfile:
            json.dump(self.annotations, outfile)
        print("Annotations saved.")

def main(input_folder, output_folder):
    app = tk.Tk()
    ImageAnnotationApp(app, "Tkinter and OpenCV", input_folder, output_folder)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Image Annotation Tool")
    parser.add_argument("-i", "--input_folder", required=True, help="Path to the folder containing images")
    parser.add_argument("-o", "--output_folder", required=True, help="Path to save the annotations")
    args = parser.parse_args()

    main(args.input_folder, args.output_folder)