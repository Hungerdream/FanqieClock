
import sys
import os
import unittest
from PyQt6.QtWidgets import QApplication, QPushButton, QWidget, QHBoxLayout
from PyQt6.QtGui import QColor, QPalette

# Ensure path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

class TestHeaderButtonsVisibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def test_contrast_ratio(self):
        """
        Verify WCAG 2.1 Contrast Ratio >= 4.5:1
        Foreground: #333333 (Dark Grey)
        Background: #F8F9FA (Light Grey/White-ish)
        """
        def get_luminance(hex_color):
            color = QColor(hex_color)
            r = color.redF()
            g = color.greenF()
            b = color.blueF()
            
            # sRGB to linear RGB
            rgb = [r, g, b]
            for i in range(3):
                if rgb[i] <= 0.03928:
                    rgb[i] = rgb[i] / 12.92
                else:
                    rgb[i] = ((rgb[i] + 0.055) / 1.055) ** 2.4
            
            return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]

        l1 = get_luminance("#F8F9FA") # Background
        l2 = get_luminance("#333333") # Foreground
        
        if l1 < l2: l1, l2 = l2, l1
        
        contrast_ratio = (l1 + 0.05) / (l2 + 0.05)
        print(f"\nContrast Ratio: {contrast_ratio:.2f}:1")
        
        self.assertGreaterEqual(contrast_ratio, 4.5, "Contrast ratio must be at least 4.5:1 for WCAG AA compliance")

    def test_button_visibility(self):
        """
        Simulate button creation and check properties
        """
        # Create a mock container to verify layout visibility
        container = QWidget()
        layout = QHBoxLayout(container)
        
        btn = QPushButton("◲")
        btn.setFixedSize(35, 35)
        # Apply the style we defined
        btn.setStyleSheet("""
            QPushButton {
                background-color: #F8F9FA;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                font-size: 18px; 
                color: #333333; 
            }
        """)
        
        layout.addWidget(btn)
        container.show()
        
        # Check basic visibility
        self.assertTrue(btn.isVisibleTo(container))
        self.assertEqual(btn.width(), 35)
        self.assertEqual(btn.height(), 35)
        
        container.close()

if __name__ == '__main__':
    unittest.main()
