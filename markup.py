import argparse
import tkinter as tk
from PIL import Image, ImageTk
import cv2
import glob
import json
import os

class ImageAnnotationApp:
    def __init__(self, window, window_title, input_folder, output_folder):
        self.window = window
        self.window.title(window_title)

        self.input_folder = input_folder
        self.output_folder = output_folder
        self.annotations = {}
        self.current_annotation_class = 1
        self.image_paths = glob.glob(f'{input_folder}/*.jpg')
        self.current_image_index = 0
        self.annotations_temp = []
        self.photo = None

        # Initialize canvas before loading images
        self.canvas = tk.Canvas(window, width=300, height=300)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self.on_canvas_click)

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

        # Load existing annotations and the first image
        self.load_existing_annotations()
        if self.image_paths:
            self.load_image(0)  # Load the first image

        self.window.mainloop()

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

        # Iterate over each annotation in the temporary annotations list
        for i, annotation in enumerate(self.annotations_temp):
            # Check if the annotation is in the expected dictionary format
            if isinstance(annotation, dict) and 'point' in annotation and 'class' in annotation:
                x, y = annotation['point']
                color = annotation['class']  # Use the color associated with the annotation
            elif isinstance(annotation, list) and len(annotation) == 2:
                # If the annotation is in a tuple (list) format, assume it's (x, y)
                x, y = annotation
                color = "red"  # Default color for tuple format annotations
            else:
                # Skip the iteration if the format is unrecognized
                continue

            r = 5  # Radius for the annotation point
            self.canvas.create_oval(x - r, y - r, x + r, y + r, fill=color)

            # Draw a line to the previous point if it's of the same class
            if i > 0:
                prev_annotation = self.annotations_temp[i - 1]
                if isinstance(prev_annotation, dict) and 'point' in prev_annotation and 'class' in prev_annotation:
                    prev_x, prev_y = prev_annotation['point']
                    prev_color = prev_annotation['class']
                elif isinstance(prev_annotation, list) and len(prev_annotation) == 2:
                    prev_x, prev_y = prev_annotation
                    prev_color = "red"
                else:
                    continue

                # Draw line if the previous annotation color matches the current one
                if prev_color == color:
                    self.canvas.create_line(prev_x, prev_y, x, y, fill=color)

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
        x, y = event.x, event.y
        annotation_class = 'blue' if self.current_annotation_class == 2 else 'red'
        new_annotation = {'point': (x, y), 'class': annotation_class}
        self.annotations_temp.append(new_annotation)
        self.draw_annotations()

    def close_app(self, event=None):
        self.save_current_annotations()  # Save annotations for the current image
        self.save_annotations()  # Save all annotations to the file
        self.window.destroy()

    def load_image(self, index):
        if 0 <= index < len(self.image_paths):
            # Load the new image
            cv_image = cv2.cvtColor(cv2.imread(self.image_paths[index]), cv2.COLOR_BGR2RGB)
            self.image = Image.fromarray(cv_image)
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
        self.canvas.delete("all")  # Clear the canvas before displaying a new image
        self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)
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
        current_image_name = os.path.basename(self.image_paths[self.current_image_index])
        self.image_name_label.config(text=f"Current Image: {current_image_name}")

    def on_canvas_click(self, event):
        x, y = event.x, event.y
        annotation_class = 'blue' if self.current_annotation_class == 2 else 'red'
        new_annotation = {'point': (x, y), 'class': annotation_class}
        self.annotations_temp.append(new_annotation)
        self.draw_annotations()


    def draw_point(self, x, y):
        r = 5
        self.canvas.create_oval(x - r, y - r, x + r, y + r, fill="red")

    def save_current_annotations(self):
        current_image_name = os.path.basename(self.image_paths[self.current_image_index])
        if current_image_name not in self.annotations:
            self.annotations[current_image_name] = {'red': [], 'blue': []}

        # Clear existing annotations for the current image before saving
        self.annotations[current_image_name]['red'].clear()
        self.annotations[current_image_name]['blue'].clear()

        for annotation in self.annotations_temp:
            if isinstance(annotation, dict) and 'class' in annotation and 'point' in annotation:
                annotation_class = annotation['class']
                self.annotations[current_image_name][annotation_class].append(annotation)

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