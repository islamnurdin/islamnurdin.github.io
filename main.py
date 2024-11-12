from PySide import QtGui, QtCore, QtWidgets
import anthropic
import FreeCAD, Part
import FreeCADGui

import os
import sys
import math
import re
import traceback

# Workbench imports
try:
    import Fem
    import ObjectsFem
    import FemGui
except ImportError:
    FreeCAD.Console.PrintWarning("FEM workbench not available\n")

try:
    import Draft
except ImportError:
    FreeCAD.Console.PrintWarning("Draft workbench not available\n")

try:
    import Sketcher
except ImportError:
    FreeCAD.Console.PrintWarning("Sketcher workbench not available\n")

try:
    import PartDesign
except ImportError:
    FreeCAD.Console.PrintWarning("PartDesign workbench not available\n")

try:
    import Path
except ImportError:
    FreeCAD.Console.PrintWarning("Path workbench not available\n")

try:
    import Mesh
except ImportError:
    FreeCAD.Console.PrintWarning("Mesh workbench not available\n")

try:
    import Points
except ImportError:
    FreeCAD.Console.PrintWarning("Points workbench not available\n")

try:
    import TechDraw
except ImportError:
    FreeCAD.Console.PrintWarning("TechDraw workbench not available\n")

try:
    import Spreadsheet
except ImportError:
    FreeCAD.Console.PrintWarning("Spreadsheet workbench not available\n")

try:
    import BOPTools
except ImportError:
    FreeCAD.Console.PrintWarning("BOPTools not available\n")

try:
    import ImportGui
except ImportError:
    FreeCAD.Console.PrintWarning("ImportGui not available\n")

try:
    import numpy
except ImportError:
    FreeCAD.Console.PrintWarning("numpy not available\n")


# Set your OpenAI API key here
client = anthropic.Anthropic(
    # defaults to os.environ.get("ANTHROPIC_API_KEY")
    api_key="key",
)

class ChatDock(QtGui.QDockWidget):
    def __init__(self, parent=None):
        super(ChatDock, self).__init__("Ask Artifex", parent)
        self.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        
        # Modern dock widget styling
        self.setStyleSheet("""
            QDockWidget {
                border: none;
                background-color: #1e1e1e;
            }
            QDockWidget::title {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 12px;
                text-align: center;
                font-weight: bold;
                font-size: 16px;
                border-bottom: 2px solid #3d3d3d;
            }
        """)

        # Create the workbench registry
        self.workbench_modules = {}
        self._initialize_workbench_modules()
        
        # Central widget setup
        widget = QtGui.QWidget()
        layout = QtGui.QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Chat display
        self.chat_display = QtGui.QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFrameStyle(QtGui.QFrame.NoFrame)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                padding: 16px;
                font-family: 'Segoe UI', Arial;
                font-size: 14px;
                color: #ffffff;
            }
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 2px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #4d4d4d;
                min-height: 30px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #5d5d5d;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        layout.addWidget(self.chat_display)
        
        # Input area container
        input_container = QtGui.QWidget()
        input_container.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
                border-radius: 12px;
                border: 1px solid #3d3d3d;
            }
        """)
        input_layout = QtGui.QHBoxLayout(input_container)
        input_layout.setContentsMargins(12, 8, 12, 8)
        input_layout.setSpacing(12)         
        # Attachment button
        self.attach_button = QtGui.QPushButton("📎")
        self.attach_button.setIcon(QtGui.QIcon.fromTheme("mail-attachment"))
        self.attach_button.setToolTip("Attach File")
        self.attach_button.setFixedSize(32, 32)
        self.attach_button.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                border: none;
                border-radius: 16px;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """)
        input_layout.addWidget(self.attach_button)
        
        # Input field
        self.chat_input = QtWidgets.QLineEdit()
        palette = self.chat_input.palette()
        self.chat_input.setPlaceholderText("What can I build for you? 💬")
        self.chat_input.returnPressed.connect(self.send_message)

        palette.setColor(QtGui.QPalette.PlaceholderText, QtGui.QColor("black"))
        self.chat_input.setPalette(palette)
        self.chat_input.setStyleSheet("""
            QLineEdit {
                border: none;
                background-color: transparent;
                color: #ffffff;
                font-family: 'Segoe UI', Arial;
                font-size: 16px;
                padding: 5px;
            }
            QLineEdit[text="What can I build for you? 💬"] {
                color: black;
            }
            QLineEdit::placeholder{
                color: black;
            }
        """)
        input_layout.addWidget(self.chat_input)
        
        # Send button
        self.send_button = QtGui.QPushButton("🛠️")
        self.send_button.setIcon(QtGui.QIcon.fromTheme("document-send"))
        self.send_button.setToolTip("Send Message")
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setFixedSize(32, 32)
        self.send_button.setStyleSheet("""
            QPushButton {
				text-align: center;
                background-color: #0066cc;
                border: none;
                border-radius: 16px;
                padding: 6px;
				font-size: 20px;
            }
            QPushButton:hover {
                background-color: #0077ee;
            }
        """)
        input_layout.addWidget(self.send_button)
        
        layout.addWidget(input_container)
        widget.setLayout(layout)
        self.setWidget(widget)
        
        widget.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
            }
        """)
        
        self.message_history = []
        self.object_registry = {}

    def format_message(self, message, is_user=True):
	    if is_user:
	        # Right-aligned user message bubble
	        return f"""
	            <div style="
	                text-align: right;
	                margin: 4px 50px;
	                background-color: none;
                	border: 1px solid #F5F4F4;
	                border-radius: 12px;
                    max-width: 300px;
	            ">
	                <div style="
	                    display: inline-block;
	                    color: #ffffff;
	                    padding: 10px 15px 10px 10px;
	                    -moz-border-radius: 12px; /* For Firefox */
	                    -webkit-border-radius: 12px; /* For Safari/Chrome */
	                    font-family: 'Segoe UI', Arial, sans-serif;
	                    font-size: 17px;
	                    max-width: 80%;
	                    word-wrap: nowrap;
	                ">
	                    {message}
	                </div>
	                <div style="
	                    color: #808080;
	                    font-size: 12px;
	                    margin-top: 4px;
	                ">
	                    You
	                </div>
	            </div>
	        """
	    else:
	        # Left-aligned assistant message bubble
	        import re
	        code_blocks = re.split(r'(```.*?```)', message, flags=re.DOTALL)
	        formatted_blocks = []
	        
	        for block in code_blocks:
	            if block.startswith('```') and block.endswith('```'):
	                code = block.strip('`').strip()
	                if code.startswith('python'):
	                    code = code[6:].strip()
	                formatted_blocks.append(f"""
	                    <div style="
							text-align: left;
	                        background-color: none;
	                        padding: 10px;
	                        border-radius: 8px;
                            border-color: white;
	                        border: 1px solid #3d3d3d;
	                        font-family: 'Consolas', 'Monaco', monospace;
	                        white-space: pre-wrap;
							line-height: 1.5;
	                        margin: 8px -40px;
	                        color: #d4d4d4;
	                        font-size: 12px;
	                    ">{code}</div><br><br>
	                """)
	            else:
	                if block.strip():
	                    formatted_blocks.append(block)
	        
	        formatted_message = ''.join(formatted_blocks)
	        
	        return f"""
				<br><div style="
						text-align: left; 
						margin: 4px -40px;
                        max-width: 140px;
	            ">
	                <div style="
	                    display: inline-block;
	                    background-color: none;
	                    color: #ffffff;
	                    padding: 10px 15px;
	                    border-radius: 12px !important;
	                    -moz-border-radius: 12px;
	                    -webkit-border-radius: 12px;
	                    font-family: 'Segoe UI', Arial, sans-serif;
	                    max-width: 80%;
	                    word-wrap: pre-wrap;
	                    border: 1px solid #3d3d3d;
						font-size: 16px;
                        max-width: 140px;
	                ">
	                    {formatted_message}
	                </div>
	                <div style="
	                    color: #808080;
	                    font-size: 12px;
	                    margin-top: 4px;
	                ">
	                    Artifex Copilot
	                </div>
	            </div>
	        """

    def get_object_state(self):
        """Get the current state of all objects in the document"""
        doc = FreeCAD.ActiveDocument
        if not doc:
            return []
        
        object_states = []
        for obj in doc.Objects:
            state = {
                'name': obj.Name,
                'type': obj.TypeId,
                'properties': {}
            }
            
            # Get basic properties
            if hasattr(obj, 'Height'):
                state['properties']['Height'] = obj.Height
            if hasattr(obj, 'Radius'):
                state['properties']['Radius'] = obj.Radius
                state['properties']['Diameter'] = obj.Radius * 2
            
            # Get placement
            if hasattr(obj, 'Placement'):
                pos = obj.Placement.Base
                state['properties']['Position'] = f"({pos.x}, {pos.y}, {pos.z})"
            
            # Get color
            if hasattr(obj, 'ViewObject') and hasattr(obj.ViewObject, 'ShapeColor'):
                color = obj.ViewObject.ShapeColor
                state['properties']['Color'] = f"({color[0]}, {color[1]}, {color[2]})"
            
            object_states.append(state)
        
        return object_states

    def build_system_message(self):
        # Get current state of all objects
        object_states = self.get_object_state()
        
        # Build object descriptions
        object_descriptions = []
        for state in object_states:
            props = [f"{k}: {v}" for k, v in state['properties'].items()]
            desc = f"{state['name']} ({state['type']}):\n " + "\n ".join(props)
            object_descriptions.append(desc)
        
        system_message = (
        "You are a FreeCAD CAD assistant specialized in FEM analysis. "
        "When generating FEM code, follow these specific guidelines:\n\n"
        
        "1. THERMAL ANALYSIS WORKFLOW:\n"
        " - Create geometry using App.activeDocument().addObject()\n"
        " - Create analysis using ObjectsFem.makeAnalysis(doc)\n"
        " - Create material using ObjectsFem.makeMaterialSolid(doc)\n"
        " - Create mesh using doc.addObject('Fem::FemMeshShapeNetgenObject')\n"
        " - Set up thermal constraints using ObjectsFem.makeConstraintTemperature(doc)\n"
        " - Create solver using ObjectsFem.makeSolverCalculixCcxTools(doc)\n"
        " - Always use FemGui.getActiveAnalysis() to access analysis object\n\n"
        
        "2. CORRECT OBJECT ACCESS:\n"
        " - Use doc.getObject('ObjectName') to access objects\n"
        " - Access analysis members through getActiveAnalysis()\n"
        " - Use proper mesh generation sequence\n"
        " - Handle constraint references correctly\n\n"
        
        "3. FEM PROPERTY ACCESS:\n"
        " - Access mesh properties through FemMesh object\n"
        " - Set solver properties through solver object\n"
        " - Use proper material property dictionary format\n"
        " - Handle boundary conditions through constraint objects\n\n"
        
        "4. EXAMPLE MATERIAL PROPERTIES:\n"
        "material = {\n"
        "    'Name': 'Copper',\n"
        "    'ThermalConductivity': '400.0 W/m/K',\n"
        "    'SpecificHeat': '385.0 J/kg/K',\n"
        "    'Density': '8960 kg/m³'\n"
        "}\n\n"
        
        "5. MESH GENERATION:\n"
        "mesh = doc.addObject('Fem::FemMeshShapeNetgenObject', 'FEMMesh')\n"
        "mesh.Shape = part\n"
        "mesh.MaxSize = 5.0\n"
        "mesh.Fineness = 'Very fine'\n"
        "mesh.SecondOrder = True\n"
        "mesh.Optimize = True\n\n"
        
        "6. SOLVER SETUP:\n"
        "solver = ObjectsFem.makeSolverCalculixCcxTools(doc)\n"
        "solver.GeometricalNonlinearity = 'linear'\n"
        "solver.ThermoMechSteadyState = True\n"
        "solver.IterationsThermoMech = 2500\n\n"
        
        "7. RESULTS HANDLING:\n"
        "results = ObjectsFem.makeResultMechanical(doc)\n"
        "fea = ccxtools.FemToolsCcx()\n"
        "fea.update_objects()\n"
        "fea.write_inp_file()\n"
        "fea.run()\n"
        "fea.load_results()\n\n"
        
        "8. ALWAYS INCLUDE ERROR HANDLING:\n"
        "try:\n"
        "    # FEM operations\n"
        "except Exception as e:\n"
        "    FreeCAD.Console.PrintError(f'FEM analysis failed: {str(e)}\\n')\n"
    )
    
        return system_message

    def _initialize_workbench_modules(self):
        """Initialize available workbench modules"""
        module_pairs = [
            ('Fem', Fem if 'Fem' in globals() else None),
            ('ObjectsFem', ObjectsFem if 'ObjectsFem' in globals() else None),
            ('Draft', Draft if 'Draft' in globals() else None),
            ('Sketcher', Sketcher if 'Sketcher' in globals() else None),
            ('PartDesign', PartDesign if 'PartDesign' in globals() else None),
            ('Path', Path if 'Path' in globals() else None),
            ('Mesh', Mesh if 'Mesh' in globals() else None),
            ('Points', Points if 'Points' in globals() else None),
            ('TechDraw', TechDraw if 'TechDraw' in globals() else None),
            ('Spreadsheet', Spreadsheet if 'Spreadsheet' in globals() else None),
            ('BOPTools', BOPTools if 'BOPTools' in globals() else None),
        ]
        
        for name, module in module_pairs:
            if module is not None:
                self.workbench_modules[name] = module
                FreeCAD.Console.PrintMessage(f"Loaded {name} workbench\n")
            else:
                FreeCAD.Console.PrintWarning(f"{name} workbench not available\n")

    def execute_code(self, code):
	    try:
	        if FreeCAD.ActiveDocument is None:
	            FreeCAD.newDocument()
	
	        # Import FEM-specific modules
	        import Fem
	        import ObjectsFem
	        import FemGui
	        from femtools import ccxtools
	        
	        # Set up global environment with FEM modules
	        global_env = {
	            'App': FreeCAD,
	            'Gui': FreeCADGui,
	            'Part': Part,
	            'FreeCAD': FreeCAD,
	            'FreeCADGui': FreeCADGui,
	            'Fem': Fem,
	            'ObjectsFem': ObjectsFem,
	            'FemGui': FemGui,
	            'ccxtools': ccxtools
	        }
	        
	        # Extract and execute code
	        code_blocks = re.findall(r'```python(.*?)```', code, re.DOTALL)
	        if code_blocks:
	            full_code = '\n'.join(block.strip() for block in code_blocks)
	            
	            # Execute with proper error handling
	            try:
	                exec(full_code, global_env)
	                FreeCAD.ActiveDocument.recompute()
	                self.chat_display.append("FEM analysis completed successfully.")
	            except Exception as e:
	                self.chat_display.append(f"FEM analysis error: {str(e)}")
	                import traceback
	                self.chat_display.append(f"Details:\n{traceback.format_exc()}")
	        else:
	            self.chat_display.append("No executable code found in response.")
	            
	    except Exception as e:
	        self.chat_display.append(f"FEM setup error: {str(e)}")


    def send_message(self):
        try:
            user_input = self.chat_input.text()
            self.message_history.append(f"User: {user_input}")

            # Format and display user message
            self.chat_display.insertHtml(self.format_message(user_input, is_user=True))
            self.chat_display.insertHtml("<br><br>")
            self.chat_display.verticalScrollBar().setValue(
                self.chat_display.verticalScrollBar().maximum()
            )
            self.chat_input.clear()

            # Build context with previous messages
            context = "\n".join(self.message_history[-6:])
            
            # Get comprehensive system message
            system_message = self.build_system_message()

            # Send request to Claude with increased token limit
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,  # Increased for complex operations
                messages=[{
                    "role": "user",
                    "content": f"Context of previous operations:\n{context}\n\n"
                              f"Generate Python code to: {user_input}"
                }],
                system=system_message,
            )

            response_text = response.content[0].text.strip()
            self.message_history.append(f"Artifex Copilot: {response_text}")

            # Display and execute response
            self.chat_display.insertHtml(self.format_message(response_text, is_user=False))
            self.chat_display.verticalScrollBar().setValue(
                self.chat_display.verticalScrollBar().maximum()
            )

            # Execute the generated code
            self.execute_code(response_text)

        except Exception as e:
            error_message = f"Error: {str(e)}"
            self.chat_display.insertHtml(self.format_message(error_message, is_user=False))
            self.chat_display.insertHtml("<br><br>")
            self.chat_display.verticalScrollBar().setValue(
                self.chat_display.verticalScrollBar().maximum()
            )

# Create and add the dock widget if it doesn't exist
if not FreeCADGui.getMainWindow().findChild(QtGui.QDockWidget, "Ask Aritfex"):
    chat_dock = ChatDock(FreeCADGui.getMainWindow())
    FreeCADGui.getMainWindow().addDockWidget(QtCore.Qt.RightDockWidgetArea, chat_dock)
