#!/usr/bin/env python3
"""
Simple offline map tile viewer using PySide6
Displays tiles downloaded from MOBAC in zoom/x/y structure
"""

import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QGraphicsView, 
                               QGraphicsScene, QVBoxLayout, QWidget, 
                               QLabel, QHBoxLayout)
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPolygonF
from PySide6.QtWidgets import QGraphicsPolygonItem


class MapViewer(QGraphicsView):
    def __init__(self, tiles_path, main_window, parent=None):
        super().__init__(parent)
        self.tiles_path = tiles_path
        self.main_window = main_window

        # set canvas up to place map items and tiles on
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        
        # enable dragging and smooth rendering
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        
        self.current_zoom = 15  # Start at zoom level 15
        
        # Load initial tiles
        self.load_tiles(update_status=False)

        # Create rover marker(represented by a triangle)
        self.rover_marker_size = 10

        triangle = QPolygonF([
        QPointF(0, -self.rover_marker_size),        # tip (forward)
        QPointF(-self.rover_marker_size / 2, self.rover_marker_size), # back-left
        QPointF(self.rover_marker_size / 2, self.rover_marker_size)   # back-right
        ])

        # adding marker to scene
        self.rover_marker = QGraphicsPolygonItem(triangle)
        self.rover_marker.setBrush(Qt.red)
        self.rover_marker.setZValue(10)
        self.scene.addItem(self.rover_marker)

        self.place_marker()
        
    def load_tiles(self, update_status=True):
        """Load all tiles for the current zoom level"""
        self.scene.clear()
        
        zoom_path = os.path.join(self.tiles_path, str(self.current_zoom))
        
        if not os.path.exists(zoom_path):
            print(f"Zoom level {self.current_zoom} not found")
            return
            
        tile_size = 256
        # finds all X coordinate folders and sorts them numerically
        x_dirs = sorted([d for d in os.listdir(zoom_path) if os.path.isdir(os.path.join(zoom_path, d))], key=int) 
        
        if not x_dirs:
            print(f"No tiles found for zoom level {self.current_zoom}")
            return
        
        min_x = None
        min_y = None
        tiles_loaded = 0
        
        # X coordinate folder create the columns of map
        for x_dir in x_dirs:
            x = int(x_dir)
            if min_x is None:
                min_x = x
            x_path = os.path.join(zoom_path, x_dir)
            
            y_files = [f for f in os.listdir(x_path) if f.endswith('.tile')]
            
            # Y coordinate folder create the rows
            for y_file in y_files:
                y_str = y_file.replace('.tile', '').replace('png', '').replace('jpg', '').replace('jpeg', '')
                try:
                    y = int(y_str)
                except ValueError:
                    print(f"Skipping invalid tile file: {y_file}")
                    continue
                    
                if min_y is None or y < min_y:
                    min_y = y
                    
                # loading and pos tile onto scene, pos is relative to min x,y
                tile_path = os.path.join(x_path, y_file)
                pixmap = QPixmap(tile_path)
                if not pixmap.isNull():
                    item = self.scene.addPixmap(pixmap)
                    item.setPos((x - (min_x or 0)) * tile_size, (y - (min_y or 0)) * tile_size)
                    tiles_loaded += 1
        
        # Store these for GPS conversion
        self.min_x = min_x if min_x is not None else 0
        self.min_y = min_y if min_y is not None else 0
        
        print(f"Loaded {tiles_loaded} tiles at zoom {self.current_zoom}")
        
        # auto zooms view to show all loaded tiles (w/ respect to aspect ratio)
        if tiles_loaded > 0:
            self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        
        if update_status and self.main_window:
            self.main_window.update_status()

        # re add rover marker ontop of tiles
        if hasattr(self, "rover_marker") and self.rover_marker is not None:
            self.scene.addItem(self.rover_marker)
            self.rover_marker.setZValue(10)
    
    # ------------------------ helper func to manage pos of rover marker ------------------------
    def place_marker(self):
        rect = self.scene.sceneRect()
        self.rover_marker.setPos(rect.center())

    def _set_marker_pos(self, x, y):
        self.rover_marker.setPos(x, y)
        
    def _set_marker_heading_deg(self, heading_deg):
        """
        heading_deg: degrees
        0 = north/up
        90 = east/right
        """
        self.rover_marker.setRotation(heading_deg)

    def update_marker(self, x, y, heading_deg=0.0):
        self._set_marker_pos(x, y)
        self._set_marker_heading_deg(heading_deg)

    # ------------------------ gps to pixel conversion ------------------------
    def lat_lon_to_tile(self, lat, lon, zoom):
        """Convert lat/lon to tile coordinates at given zoom level"""
        import math
        n = 2 ** zoom   # tiles req for grid size

        # (lon + 180) / 360 this gets ( 0 for far west, 1 for far east)
        x_tile = (lon + 180) / 360
        # multi by n to get the tile num
        x_tile = x_tile * n

        # Convert degrees to radians (needed for trig functions)
        lat_rad = math.radians(lat)

        # web mercator formula, calc for curvature
        inner = math.tan(lat_rad) + 1 / math.cos(lat_rad)
        mercator_y = math.log(inner) / math.pi

        # Normalize to 0-1 range (flip because Y=0 is north)
        y_fraction = (1 - mercator_y) / 2

        # Scale to tile coordinates
        y_tile = y_fraction * n
        
        return x_tile, y_tile

    def lat_lon_to_scene_pos(self, lat, lon):
        """Convert GPS coordinates to scene pixel position"""
        # Get tile coordinates
        x_tile, y_tile = self.lat_lon_to_tile(lat, lon, self.current_zoom)
        
        # Convert to pixel position (tiles are 256x256)
        tile_size = 256
        x_pixel = x_tile * tile_size
        y_pixel = y_tile * tile_size
        
        # Adjust for the tile offset used when loading tiles
        # You'll need to track min_x and min_y from load_tiles
        x_pixel -= self.min_x * tile_size if hasattr(self, 'min_x') else 0
        y_pixel -= self.min_y * tile_size if hasattr(self, 'min_y') else 0
        
        return x_pixel, y_pixel

    def update_marker_gps(self, lat, lon, heading_deg=0.0):
        """Update marker using GPS coordinates"""
        x, y = self.lat_lon_to_scene_pos(lat, lon)
        self.update_marker(x, y, heading_deg)

    def wheelEvent(self, event):
        """Zoom in/out with mouse wheel"""
        # Zoom with Ctrl+Wheel, otherwise just scale the view
        if event.modifiers() & Qt.ControlModifier:
            # Change zoom level
            if event.angleDelta().y() > 0:
                self.current_zoom = min(self.current_zoom + 1, 19)
            else:
                self.current_zoom = max(self.current_zoom - 1, 12)
            self.load_tiles()
        else:
            # Scale the current view
            factor = 1.15
            if event.angleDelta().y() > 0:
                self.scale(factor, factor)
            else:
                self.scale(1.0 / factor, 1.0 / factor)


class MainWindow(QMainWindow):
    def __init__(self, tiles_path):
        super().__init__()
        self.setWindowTitle("Offline Map Viewer")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create layout
        layout = QVBoxLayout(central_widget)
        
        # Create status labels first (before map viewer)
        status_layout = QHBoxLayout()
        self.zoom_label = QLabel()
        self.help_label = QLabel("Controls: Drag to pan | Scroll to scale view | Ctrl+Scroll to change zoom level")
        status_layout.addWidget(self.zoom_label)
        status_layout.addStretch()
        status_layout.addWidget(self.help_label)
        
        # Create map viewer (this will call update_status)
        self.map_viewer = MapViewer(tiles_path, self)
        layout.addWidget(self.map_viewer)
        
        # Add status bar at bottom
        layout.addLayout(status_layout)
        
        self.update_status()
        
    def update_status(self):
        self.zoom_label.setText(f"Zoom Level: {self.map_viewer.current_zoom}")


def main():
    # Path to your tiles
    TILES_PATH = "MDRS_2025-11-25_163543/Bing Satellite"
    
    if len(sys.argv) > 1: TILES_PATH = sys.argv[1]
    
    if not os.path.exists(TILES_PATH):
        print(f"Error: Tiles path not found: {TILES_PATH}")
        print(f"Usage: python map_viewer.py [path_to_tiles]")
        print(f"Example: python map_viewer.py 'MDRS_2025-11-25_163543/Bing Satellite'")
        sys.exit(1)
    
    app = QApplication(sys.argv)
    window = MainWindow(TILES_PATH)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()