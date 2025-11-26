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

class MapViewer(QGraphicsView):
    def __init__(self, tiles_path, main_window, parent=None):
        super().__init__(parent)
        self.tiles_path = tiles_path
        self.main_window = main_window
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        
        # Enable dragging and smooth rendering
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        
        # Current zoom level
        self.current_zoom = 15  # Start at zoom level 15
        
        # Load initial tiles
        self.load_tiles(update_status=False)
        
    def load_tiles(self, update_status=True):
        """Load all tiles for the current zoom level"""
        self.scene.clear()
        
        zoom_path = os.path.join(self.tiles_path, str(self.current_zoom))
        
        if not os.path.exists(zoom_path):
            print(f"Zoom level {self.current_zoom} not found")
            return
            
        # Tile size (standard is 256x256)
        tile_size = 256
        
        # Get all x directories
        x_dirs = sorted([d for d in os.listdir(zoom_path) if os.path.isdir(os.path.join(zoom_path, d))], key=int)
        
        if not x_dirs:
            print(f"No tiles found for zoom level {self.current_zoom}")
            return
        
        # Track min coordinates for centering
        min_x = None
        min_y = None
        tiles_loaded = 0
        
        for x_dir in x_dirs:
            x = int(x_dir)
            if min_x is None:
                min_x = x
            x_path = os.path.join(zoom_path, x_dir)
            
            # Get all y tile files
            y_files = [f for f in os.listdir(x_path) if f.endswith('.tile')]
            
            for y_file in y_files:
                # Extract y coordinate from filename (handle various formats)
                y_str = y_file.replace('.tile', '').replace('png', '').replace('jpg', '').replace('jpeg', '')
                try:
                    y = int(y_str)
                except ValueError:
                    print(f"Skipping invalid tile file: {y_file}")
                    continue
                    
                if min_y is None or y < min_y:
                    min_y = y
                    
                tile_path = os.path.join(x_path, y_file)
                
                # Load the tile
                pixmap = QPixmap(tile_path)
                if not pixmap.isNull():
                    # Position the tile relative to origin
                    item = self.scene.addPixmap(pixmap)
                    item.setPos((x - (min_x or 0)) * tile_size, (y - (min_y or 0)) * tile_size)
                    tiles_loaded += 1
        
        print(f"Loaded {tiles_loaded} tiles at zoom {self.current_zoom}")
        
        # Fit the view to show all tiles
        if tiles_loaded > 0:
            self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        
        # Update status only if main window is available
        if update_status and self.main_window:
            self.main_window.update_status()
        
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
    # Path to your tiles (modify this!)
    TILES_PATH = "MDRS_2025-11-25_163543/Bing Satellite"
    
    if len(sys.argv) > 1:
        TILES_PATH = sys.argv[1]
    
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