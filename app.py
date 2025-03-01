import os
import logging
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from werkzeug.utils import secure_filename
from document_processor import process_document
from ai_analyzer import analyze_document
from core_api import CoreAPI
from manim import *
import tempfile
import shutil
import time

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Video generation configuration
VIDEO_OUTPUT_DIR = os.path.join('static', 'videos')
if not os.path.exists(VIDEO_OUTPUT_DIR):
    os.makedirs(VIDEO_OUTPUT_DIR)

# Initialize CORE API client with configuration from environment variables
core_api = CoreAPI(
    api_key=os.getenv('CORE_API_KEY'),
    api_url=os.getenv('CORE_API_URL')
)

# File upload configuration
UPLOAD_FOLDER = '/tmp/uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['GET'])
def search_papers():
    """Main search endpoint that handles both HTML and JSON responses"""
    query = request.args.get('q', '')
    page = int(request.args.get('page', 1))

    if request.args.get('format') == 'json':
        try:
            search_results = core_api.search_papers(query, page_size=5)
            if search_results:
                return jsonify(search_results)
            return jsonify({'error': 'No results found'}), 404
        except ValueError as e:
            logger.error(f"API configuration error: {str(e)}")
            return jsonify({'error': 'API configuration error. Please check API key.'}), 500
        except Exception as e:
            logger.error(f"JSON search error: {str(e)}")
            return jsonify({'error': 'Search failed'}), 500

    if not query:
        return redirect(url_for('index'))

    try:
        search_results = core_api.search_papers(query, page=page)
        if search_results:
            return render_template('search_results.html',
                               query=query,
                               results=search_results['results'],
                               total_hits=search_results['total_hits'],
                               page=search_results['page'],
                               page_size=search_results['page_size'])
        else:
            flash('Error searching papers. Please verify API configuration.', 'error')
            return redirect(url_for('index'))

    except ValueError as e:
        logger.error(f"API configuration error: {str(e)}")
        flash('API configuration error. Please check API key.', 'error')
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        flash('Error searching papers', 'error')
        return redirect(url_for('index'))

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('index'))

    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('index'))

    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Process document
            text_content = process_document(filepath)

            try:
                # Analyze document with error handling
                analysis_result = analyze_document(text_content)
            except ConnectionError as e:
                logger.error(f"Failed to connect to Ollama: {str(e)}")
                flash('Unable to connect to Ollama service. Make sure Ollama is running.', 'error')
                return redirect(url_for('index'))
            except ValueError as e:
                logger.error(f"API configuration error: {str(e)}")
                flash('Ollama configuration error. Please check your settings.', 'error')
                return redirect(url_for('index'))
            except Exception as e:
                logger.error(f"AI analysis error: {str(e)}")
                flash('Error analyzing document', 'error')
                return redirect(url_for('index'))
            finally:
                # Cleanup file
                if os.path.exists(filepath):
                    os.remove(filepath)

            return render_template('analysis.html', 
                                   analysis=analysis_result,
                                   filename=filename)

        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            flash('Error processing file', 'error')
            return redirect(url_for('index'))

    flash('Invalid file type', 'error')
    return redirect(url_for('index'))

@app.route('/notebook')
def notebook():
    return render_template('notebook.html')

@app.route('/generate-image', methods=['POST'])
def generate_image():
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        if not prompt:
            return jsonify({'error': 'No prompt provided'}), 400

        # TODO: Implement actual image generation
        # For now, return a placeholder
        return jsonify({
            'url': 'https://via.placeholder.com/500x300?text=Generated+Image'
        })
    except Exception as e:
        logger.error(f"Image generation error: {str(e)}")
        return jsonify({'error': 'Failed to generate image'}), 500

@app.route('/check-plagiarism', methods=['POST'])
def check_plagiarism():
    try:
        data = request.get_json()
        content = data.get('content')
        if not content:
            return jsonify({'error': 'No content provided'}), 400

        # TODO: Implement actual plagiarism checking
        # For now, return placeholder data
        return jsonify({
            'similarity': 15,
            'matches': [
                {'source': 'Sample source 1', 'similarity': 10},
                {'source': 'Sample source 2', 'similarity': 5}
            ]
        })
    except Exception as e:
        logger.error(f"Plagiarism check error: {str(e)}")
        return jsonify({'error': 'Failed to check plagiarism'}), 500
        
@app.route('/summarize-paper', methods=['POST'])
def summarize_paper():
    try:
        data = request.get_json()
        title = data.get('title')
        abstract = data.get('abstract')
        
        if not title or not abstract:
            return jsonify({'error': 'Title and abstract are required'}), 400
            
        try:
            # Create a structured prompt for the Mistral model
            prompt = f"""Please analyze this research paper and provide a structured summary.
Title: {title}

Abstract: {abstract}

Please provide a detailed analysis in the following format:

1. Key Points:
- List the main points and contributions
- Highlight innovative aspects

2. Methodology:
- Research methods used
- Experimental setup
- Data collection approach

3. Findings:
- Main results
- Statistical significance
- Key discoveries

4. Conclusions:
- Main takeaways
- Implications
- Future work suggestions

Please be concise but comprehensive in your analysis."""

            logger.debug(f"Sending text to Ollama for summarization. Length: {len(prompt)}")
            
            # Get summary from Ollama's Mistral model
            summary_result = analyze_document(prompt, is_summary=True)
            
            # Parse the structured response
            sections = {
                'key_points': [],
                'methodology': [],
                'findings': [],
                'conclusions': []
            }
            
            current_section = None
            for line in summary_result.get('response', '').split('\n'):
                line = line.strip()
                if not line:
                    continue
                
                # Check for section headers
                lower_line = line.lower()
                if 'key points' in lower_line:
                    current_section = 'key_points'
                    continue
                elif 'methodology' in lower_line:
                    current_section = 'methodology'
                    continue
                elif 'findings' in lower_line:
                    current_section = 'findings'
                    continue
                elif 'conclusions' in lower_line:
                    current_section = 'conclusions'
                    continue
                
                # Add points to appropriate section
                if current_section and line.startswith('-'):
                    point = line[1:].strip()  # Remove the bullet point
                    if point:
                        sections[current_section].append(point)
            
            # Generate video from structured summary
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    class EnhancedSummaryScene(Scene):
                        def construct(self):
                            # Display title with animation
                            title_text = Text(title, font_size=36, color=BLUE)
                            title_text.to_edge(UP)
                            self.play(Write(title_text))
                            self.wait(2)
                            
                            # Animate title to smaller size and move to top
                            small_title = Text(title, font_size=24, color=BLUE)
                            small_title.to_edge(UP)
                            self.play(Transform(title_text, small_title))
                            
                            # Initialize section displays
                            current_section_title = None
                            current_points = None
                            
                            # Display sections with improved animations
                            sections_data = [
                                ("Key Points", sections['key_points'], RED),
                                ("Methodology", sections['methodology'], GREEN),
                                ("Findings", sections['findings'], YELLOW),
                                ("Conclusions", sections['conclusions'], PURPLE)
                            ]
                            
                            for section_title, points, color in sections_data:
                                if points:
                                    # Clear previous section with fade
                                    if current_section_title:
                                        self.play(
                                            FadeOut(current_section_title),
                                            *[FadeOut(point) for point in current_points]
                                        )
                                    
                                    # Display section title with animation
                                    current_section_title = Text(
                                        section_title,
                                        font_size=28,
                                        color=color
                                    ).next_to(small_title, DOWN, buff=0.5)
                                    
                                    self.play(
                                        Write(current_section_title),
                                        run_time=1
                                    )
                                    
                                    # Display points with enhanced animations
                                    current_points = VGroup()
                                    for i, point in enumerate(points):
                                        # Create bullet point
                                        bullet = Text("•", font_size=24).shift(DOWN * (i + 2) * 0.7)
                                        
                                        # Format point text with word wrap
                                        words = point.split()
                                        lines = []
                                        current_line = []
                                        
                                        for word in words:
                                            current_line.append(word)
                                            if len(' '.join(current_line)) > 60:
                                                lines.append(' '.join(current_line[:-1]))
                                                current_line = [word]
                                        
                                        if current_line:
                                            lines.append(' '.join(current_line))
                                        
                                        # Create text for each line
                                        point_text = VGroup()
                                        for j, line in enumerate(lines):
                                            line_text = Text(
                                                line,
                                                font_size=20
                                            ).next_to(bullet, RIGHT, buff=0.2).shift(DOWN * j * 0.4)
                                            point_text.add(line_text)
                                        
                                        point_group = VGroup(bullet, point_text)
                                        current_points.add(point_group)
                                    
                                    # Animate points appearing one by one
                                    for point in current_points:
                                        self.play(
                                            Write(point),
                                            run_time=1
                                        )
                                    self.wait(3)
                            
                            # Final animation
                            if current_section_title:
                                self.play(
                                    FadeOut(current_section_title),
                                    *[FadeOut(point) for point in current_points]
                                )
                            
                            # Conclusion animation with particles
                            conclusion = Text("Summary Complete", font_size=36, color=BLUE)
                            self.play(
                                Write(conclusion),
                                run_time=1.5
                            )
                            self.wait(2)
                            self.play(FadeOut(conclusion))

                    # Configure Manim
                    config.media_dir = temp_dir
                    config.video_dir = temp_dir
                    config.output_file = "summary_visualization"

                    # Render the scene
                    scene = EnhancedSummaryScene()
                    scene.render()

                    # Move the output video to static directory
                    output_path = os.path.join(temp_dir, 'videos', 'EnhancedSummaryScene.mp4')
                    if os.path.exists(output_path):
                        video_filename = f'summary_viz_{int(time.time())}.mp4'
                        target_path = os.path.join(VIDEO_OUTPUT_DIR, video_filename)
                        shutil.copy2(output_path, target_path)
                        
                        # Check if the request wants JSON response
                        if request.headers.get('Accept') == 'application/json':
                            return jsonify({
                                'success': True,
                                'summary': summary_result.get('response', ''),
                                'structured_summary': sections,
                                'video_url': url_for('static', filename=f'videos/{video_filename}')
                            })
                        
                        # Otherwise render the template
                        return render_template('analysis.html',
                                            title=title,
                                            summary=summary_result.get('response', ''),
                                            structured_summary=sections,
                                            video_url=url_for('static', filename=f'videos/{video_filename}'))
                    
            except Exception as video_error:
                logger.error(f"Video generation error: {str(video_error)}")
                if request.headers.get('Accept') == 'application/json':
                    return jsonify({
                        'success': True,
                        'summary': summary_result.get('response', ''),
                        'structured_summary': sections,
                        'video_error': str(video_error)
                    })
                flash('Error generating video visualization', 'error')
                return render_template('analysis.html',
                                    title=title,
                                    summary=summary_result.get('response', ''),
                                    structured_summary=sections)
            
        except ConnectionError as e:
            logger.error(f"Failed to connect to Ollama: {str(e)}")
            return jsonify({'error': 'Unable to connect to Ollama service. Make sure Ollama is running.'}), 500
        except Exception as e:
            logger.error(f"AI analysis error: {str(e)}")
            return jsonify({'error': f'Error analyzing paper: {str(e)}'}), 500
            
    except Exception as e:
        logger.error(f"Paper summarization error: {str(e)}")
        return jsonify({'error': 'Failed to summarize paper'}), 500

@app.route('/generate-video', methods=['POST'])
def generate_video():
    try:
        data = request.get_json()
        paper_content = data.get('content')
        equations = data.get('equations', [])
        
        if not paper_content and not equations:
            return jsonify({'error': 'No content or equations provided'}), 400

        # Create a temporary directory for Manim output
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create Manim scene class dynamically
            class MathScene(Scene):
                def construct(self):
                    # Title
                    title = Text("Mathematical Visualization", font_size=40)
                    self.play(Write(title))
                    self.wait(1)
                    self.play(FadeOut(title))

                    # Display equations one by one
                    for eq in equations:
                        math_eq = MathTex(eq, font_size=36)
                        self.play(Write(math_eq))
                        self.wait(2)
                        self.play(FadeOut(math_eq))

            # Configure Manim
            config.media_dir = temp_dir
            config.video_dir = temp_dir
            config.output_file = "math_visualization"

            # Render the scene
            scene = MathScene()
            scene.render()

            # Move the output video to static directory
            output_path = os.path.join(temp_dir, 'videos', 'MathScene.mp4')
            if os.path.exists(output_path):
                video_filename = f'math_viz_{int(time.time())}.mp4'
                target_path = os.path.join(VIDEO_OUTPUT_DIR, video_filename)
                shutil.copy2(output_path, target_path)
                
                return jsonify({
                    'success': True,
                    'video_url': url_for('static', filename=f'videos/{video_filename}')
                })
            else:
                return jsonify({'error': 'Failed to generate video'}), 500

    except Exception as e:
        logger.error(f"Video generation error: {str(e)}")
        return jsonify({'error': f'Failed to generate video: {str(e)}'}), 500

@app.errorhandler(413)
def too_large(e):
    flash('File is too large (max 16MB)', 'error')
    return redirect(url_for('index'))

@app.errorhandler(500)
def server_error(e):
    flash('Server error occurred', 'error')
    return redirect(url_for('index'))