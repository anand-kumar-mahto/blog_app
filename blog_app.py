import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
import os
import json
from datetime import datetime
import re
from tkinter import ttk
import webbrowser


class BlogPost:
    def __init__(self, title, content, timestamp=None, category="", tags=None):
        self.title = title
        self.content = content
        if timestamp is None:
            self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            self.timestamp = timestamp
        self.category = category
        self.tags = tags if tags is not None else []

    def to_dict(self):
        return {
            "title": self.title,
            "content": self.content,
            "timestamp": self.timestamp,
            "category": self.category,
            "tags": self.tags
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            data["title"], 
            data["content"], 
            data["timestamp"],
            data.get("category", ""),
            data.get("tags", [])
        )

    def matches_search(self, query):
        """Check if the post matches a search query"""
        query = query.lower()
        return (query in self.title.lower() or 
                query in self.content.lower() or
                query in self.category.lower() or
                any(query in tag.lower() for tag in self.tags))


class EnhancedBlogApp:
    def __init__(self, root):
        self.root = root
        self.root.title(" personal blog")
        self.root.geometry("1100x750")
        
        self.posts = []
        self.current_post_index = None
        self.filtered_posts = []  # For search functionality
        self.filtered_indices = []  # Map filtered indices to original indices
        
        # Data file path
        self.data_file = "blog_posts.json"
        self.backup_file = "blog_posts_backup.json"

        # Create menu
        self.create_menu()

        # Create toolbar
        self.create_toolbar()

        # Main frame
        self.main_frame = tk.Frame(root)
        self.main_frame.pack(pady=10, fill=tk.BOTH, expand=True)

        # Left frame for posts list and search
        self.left_frame = tk.Frame(self.main_frame)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 5))

        # Search frame
        self.search_frame = tk.Frame(self.left_frame)
        self.search_frame.pack(fill=tk.X, pady=(0, 10))

        self.search_label = tk.Label(self.search_frame, text="Search:", font=("Arial", 10))
        self.search_label.pack(side=tk.LEFT)

        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.on_search_change)
        self.search_entry = tk.Entry(self.search_frame, textvariable=self.search_var, font=("Arial", 10))
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))

        self.clear_search_button = tk.Button(self.search_frame, text="Clear", command=self.clear_search, 
                                           font=("Arial", 8))
        self.clear_search_button.pack(side=tk.LEFT)

        # Label for posts list
        self.posts_label = tk.Label(self.left_frame, text="Blog Posts", font=("Arial", 14, "bold"))
        self.posts_label.pack()

        # Listbox to display blog posts
        self.post_listbox = tk.Listbox(self.left_frame, width=50, height=20, font=("Arial", 10))
        self.post_listbox.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        # Scrollbar for the listbox
        self.scrollbar = tk.Scrollbar(self.left_frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.post_listbox.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.post_listbox.yview)

        # Bind selection event
        self.post_listbox.bind('<<ListboxSelect>>', self.on_post_select)

        # Right frame for text area and formatting tools
        self.right_frame = tk.Frame(self.main_frame)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 10))

        # Formatting toolbar
        self.create_formatting_toolbar()

        # Label for editor
        self.editor_label = tk.Label(self.right_frame, text="Post Content", font=("Arial", 14, "bold"))
        self.editor_label.pack()

        # Text area for editing blog post with scrollbar
        self.text_frame = tk.Frame(self.right_frame)
        self.text_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        self.text_area = tk.Text(self.text_frame, width=60, height=15, font=("Arial", 11), wrap=tk.WORD)
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.text_scrollbar = tk.Scrollbar(self.text_frame)
        self.text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.text_area.config(yscrollcommand=self.text_scrollbar.set)
        self.text_scrollbar.config(command=self.text_area.yview)

        # Word count label
        self.word_count_var = tk.StringVar()
        self.word_count_var.set("Words: 0 | Characters: 0")
        self.word_count_label = tk.Label(self.right_frame, textvariable=self.word_count_var, 
                                       font=("Arial", 9), fg="gray")
        self.word_count_label.pack(anchor=tk.E, pady=(2, 2))

        # Bind text change event for word count
        self.text_area.bind('<KeyRelease>', self.update_word_count)
        self.text_area.bind('<Button-1>', self.update_word_count)

        # Category and tags frame
        self.meta_frame = tk.Frame(self.right_frame)
        self.meta_frame.pack(fill=tk.X, pady=(5, 0))

        # Category
        self.category_label = tk.Label(self.meta_frame, text="Category:", font=("Arial", 10))
        self.category_label.pack(anchor=tk.W)
        self.category_var = tk.StringVar()
        self.category_entry = tk.Entry(self.meta_frame, textvariable=self.category_var, font=("Arial", 10))
        self.category_entry.pack(fill=tk.X, pady=(0, 5))

        # Tags
        self.tags_label = tk.Label(self.meta_frame, text="Tags (comma separated):", font=("Arial", 10))
        self.tags_label.pack(anchor=tk.W)
        self.tags_var = tk.StringVar()
        self.tags_entry = tk.Entry(self.meta_frame, textvariable=self.tags_var, font=("Arial", 10))
        self.tags_entry.pack(fill=tk.X)

        # Buttons frame
        self.buttons_frame = tk.Frame(root)
        self.buttons_frame.pack(pady=10)

        # Buttons for actions
        self.create_button = tk.Button(self.buttons_frame, text="Create Post", command=self.create_post, 
                                      bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), width=12)
        self.create_button.pack(side=tk.LEFT, padx=5)

        self.edit_button = tk.Button(self.buttons_frame, text="Edit Post", command=self.edit_post, 
                                    bg="#2196F3", fg="white", font=("Arial", 10, "bold"), width=12)
        self.edit_button.pack(side=tk.LEFT, padx=5)

        self.delete_button = tk.Button(self.buttons_frame, text="Delete Post", command=self.delete_post, 
                                      bg="#F44336", fg="white", font=("Arial", 10, "bold"), width=12)
        self.delete_button.pack(side=tk.LEFT, padx=5)

        self.clear_button = tk.Button(self.buttons_frame, text="Clear Editor", command=self.clear_editor, 
                                     bg="#FF9800", fg="white", font=("Arial", 10, "bold"), width=12)
        self.clear_button.pack(side=tk.LEFT, padx=5)

        self.preview_button = tk.Button(self.buttons_frame, text="Preview", command=self.preview_post, 
                                       bg="#9C27B0", fg="white", font=("Arial", 10, "bold"), width=12)
        self.preview_button.pack(side=tk.LEFT, padx=5)

        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Welcome to Enhanced Blog App! Create your first post.")
        self.status_bar = tk.Label(root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Load posts on startup
        self.load_posts()
        self.update_word_count(None)

    def create_menu(self):
        """Create the menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Post", command=self.create_post)
        file_menu.add_command(label="Save Post", command=self.save_current_post)
        file_menu.add_separator()
        file_menu.add_command(label="Export as HTML", command=self.export_as_html)
        file_menu.add_command(label="Export as PDF", command=self.export_as_pdf)
        file_menu.add_separator()
        file_menu.add_command(label="Backup Data", command=self.backup_data)
        file_menu.add_command(label="Restore Data", command=self.restore_data)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Clear Editor", command=self.clear_editor)
        edit_menu.add_separator()
        edit_menu.add_command(label="Bold", command=self.format_bold)
        edit_menu.add_command(label="Italic", command=self.format_italic)
        edit_menu.add_command(label="Underline", command=self.format_underline)

        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Refresh Posts", command=self.refresh_posts)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

    def create_toolbar(self):
        """Create a toolbar with quick actions"""
        self.toolbar = tk.Frame(self.root, bd=1, relief=tk.RAISED)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)

        # Add buttons to toolbar
        new_btn = tk.Button(self.toolbar, text="New", command=self.create_post, 
                           relief=tk.FLAT, font=("Arial", 9))
        new_btn.pack(side=tk.LEFT, padx=2, pady=2)

        save_btn = tk.Button(self.toolbar, text="Save", command=self.save_current_post, 
                            relief=tk.FLAT, font=("Arial", 9))
        save_btn.pack(side=tk.LEFT, padx=2, pady=2)

        delete_btn = tk.Button(self.toolbar, text="Delete", command=self.delete_post, 
                              relief=tk.FLAT, font=("Arial", 9))
        delete_btn.pack(side=tk.LEFT, padx=2, pady=2)

        preview_btn = tk.Button(self.toolbar, text="Preview", command=self.preview_post, 
                               relief=tk.FLAT, font=("Arial", 9))
        preview_btn.pack(side=tk.LEFT, padx=2, pady=2)

    def create_formatting_toolbar(self):
        """Create formatting toolbar for text editor"""
        self.format_toolbar = tk.Frame(self.right_frame)
        self.format_toolbar.pack(fill=tk.X, pady=(0, 5))

        bold_btn = tk.Button(self.format_toolbar, text="B", command=self.format_bold, 
                            font=("Arial", 9, "bold"), width=3)
        bold_btn.pack(side=tk.LEFT, padx=2)

        italic_btn = tk.Button(self.format_toolbar, text="I", command=self.format_italic, 
                              font=("Arial", 9, "italic"), width=3)
        italic_btn.pack(side=tk.LEFT, padx=2)

        underline_btn = tk.Button(self.format_toolbar, text="U", command=self.format_underline, 
                                 font=("Arial", 9, "underline"), width=3)
        underline_btn.pack(side=tk.LEFT, padx=2)

    def format_bold(self):
        """Apply bold formatting to selected text"""
        try:
            selected_text = self.text_area.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.text_area.insert(tk.SEL_FIRST, "**")
            self.text_area.insert(tk.SEL_LAST, "**")
        except tk.TclError:
            # No text selected
            pass

    def format_italic(self):
        """Apply italic formatting to selected text"""
        try:
            selected_text = self.text_area.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.text_area.insert(tk.SEL_FIRST, "*")
            self.text_area.insert(tk.SEL_LAST, "*")
        except tk.TclError:
            # No text selected
            pass

    def format_underline(self):
        """Apply underline formatting to selected text"""
        try:
            selected_text = self.text_area.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.text_area.insert(tk.SEL_FIRST, "__")
            self.text_area.insert(tk.SEL_LAST, "__")
        except tk.TclError:
            # No text selected
            pass

    def update_word_count(self, event):
        """Update word and character count"""
        content = self.text_area.get("1.0", tk.END)
        words = len(content.split())
        chars = len(content) - 1  # -1 for the extra newline
        self.word_count_var.set(f"Words: {words} | Characters: {chars}")

    def on_search_change(self, *args):
        """Handle search input changes"""
        query = self.search_var.get()
        self.filter_posts(query)

    def filter_posts(self, query):
        """Filter posts based on search query"""
        if not query:
            # If no query, show all posts
            self.filtered_posts = self.posts.copy()
            self.filtered_indices = list(range(len(self.posts)))
            self.refresh_post_list()
            return

        # Filter posts that match the query
        self.filtered_posts = []
        self.filtered_indices = []
        for i, post in enumerate(self.posts):
            if post.matches_search(query):
                self.filtered_posts.append(post)
                self.filtered_indices.append(i)
        
        self.refresh_post_list()

    def clear_search(self):
        """Clear the search box and show all posts"""
        self.search_var.set("")
        self.filter_posts("")

    def refresh_post_list(self):
        """Refresh the post list display"""
        # Clear listbox
        self.post_listbox.delete(0, tk.END)
        
        # Populate with filtered posts
        for post in self.filtered_posts:
            self.post_listbox.insert(tk.END, f"{post.title} ({post.timestamp})")
        
        # Update status
        if self.search_var.get():
            self.status_var.set(f"Showing {len(self.filtered_posts)} of {len(self.posts)} posts")
        else:
            self.status_var.set(f"Showing all {len(self.posts)} posts")

    def refresh_posts(self):
        """Refresh the posts list"""
        self.clear_search()
        self.status_var.set(f"Refreshed. Showing all {len(self.posts)} posts")

    def load_posts(self):
        """Load posts from a JSON file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as file:
                    posts_data = json.load(file)
                    self.posts = [BlogPost.from_dict(data) for data in posts_data]
                    
                # Initialize filtered posts
                self.filtered_posts = self.posts.copy()
                self.filtered_indices = list(range(len(self.posts)))
                
                # Clear listbox and populate with loaded posts
                self.post_listbox.delete(0, tk.END)
                for post in self.filtered_posts:
                    self.post_listbox.insert(tk.END, f"{post.title} ({post.timestamp})")
                    
                self.status_var.set(f"Loaded {len(self.posts)} posts from file.")
            else:
                self.status_var.set("No existing posts found. Create your first post!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load posts: {str(e)}")
            self.status_var.set("Error loading posts.")

    def save_posts(self):
        """Save posts to a JSON file"""
        try:
            posts_data = [post.to_dict() for post in self.posts]
            with open(self.data_file, 'w') as file:
                json.dump(posts_data, file, indent=2)
            self.status_var.set(f"Saved {len(self.posts)} posts to file.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save posts: {str(e)}")
            self.status_var.set("Error saving posts.")

    def backup_data(self):
        """Backup posts to a separate file"""
        try:
            posts_data = [post.to_dict() for post in self.posts]
            with open(self.backup_file, 'w') as file:
                json.dump(posts_data, file, indent=2)
            messagebox.showinfo("Backup", f"Successfully backed up {len(self.posts)} posts!")
            self.status_var.set(f"Backed up {len(self.posts)} posts.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to backup posts: {str(e)}")
            self.status_var.set("Error backing up posts.")

    def restore_data(self):
        """Restore posts from backup file"""
        try:
            if os.path.exists(self.backup_file):
                result = messagebox.askyesno("Confirm Restore", 
                                           "Are you sure you want to restore from backup? This will replace all current posts.")
                if result:
                    with open(self.backup_file, 'r') as file:
                        posts_data = json.load(file)
                        self.posts = [BlogPost.from_dict(data) for data in posts_data]
                        
                    # Save to main file and refresh
                    self.save_posts()
                    self.filtered_posts = self.posts.copy()
                    self.filtered_indices = list(range(len(self.posts)))
                    self.refresh_post_list()
                    self.clear_editor()
                    messagebox.showinfo("Restore", f"Successfully restored {len(self.posts)} posts!")
            else:
                messagebox.showwarning("Restore", "No backup file found!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to restore posts: {str(e)}")
            self.status_var.set("Error restoring posts.")

    def export_as_html(self):
        """Export current post as HTML"""
        if self.current_post_index is not None:
            post = self.posts[self.current_post_index]
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{post.title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #333; }}
        .meta {{ color: #666; font-size: 0.9em; }}
        .content {{ margin-top: 20px; line-height: 1.6; }}
        .category {{ background: #e0e0e0; padding: 2px 6px; border-radius: 3px; }}
        .tags {{ margin-top: 10px; }}
        .tag {{ background: #4CAF50; color: white; padding: 2px 6px; border-radius: 3px; margin-right: 5px; }}
    </style>
</head>
<body>
    <h1>{post.title}</h1>
    <div class="meta">
        <span>Published: {post.timestamp}</span>
        <span class="category">Category: {post.category}</span>
    </div>
    <div class="content">
        {self.format_text_for_html(post.content)}
    </div>
    <div class="tags">
        Tags: {' '.join(f'<span class="tag">{tag}</span>' for tag in post.tags)}
    </div>
</body>
</html>
            """
            
            file_path = filedialog.asksaveasfilename(
                defaultextension=".html",
                filetypes=[("HTML files", "*.html"), ("All files", "*.*")]
            )
            
            if file_path:
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    messagebox.showinfo("Export", "Post exported as HTML successfully!")
                    self.status_var.set("Post exported as HTML.")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to export post: {str(e)}")
        else:
            messagebox.showwarning("Export", "Select a post to export!")

    def format_text_for_html(self, text):
        """Simple formatting for HTML export"""
        # Convert markdown-style formatting to HTML
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)  # Bold
        text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)  # Italic
        text = re.sub(r'__(.*?)__', r'<u>\1</u>', text)  # Underline
        # Convert newlines to paragraphs
        paragraphs = text.split('\n\n')
        return '\n\n'.join(f'<p>{p}</p>' for p in paragraphs if p.strip())

    def export_as_pdf(self):
        """Export current post as PDF (placeholder)"""
        if self.current_post_index is not None:
            messagebox.showinfo("Export", "PDF export feature would be implemented with a PDF library.\n\nThis is a placeholder for the functionality.")
        else:
            messagebox.showwarning("Export", "Select a post to export!")

    def create_post(self):
        """Create a new blog post"""
        title = simpledialog.askstring("Post Title", "Enter the title of the post:")
        if title:
            content = self.text_area.get("1.0", tk.END).strip()
            if content:
                # Get category and tags
                category = self.category_var.get()
                tags_str = self.tags_var.get()
                tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
                
                # Create new post
                new_post = BlogPost(title, content, category=category, tags=tags)
                self.posts.append(new_post)
                
                # Add to filtered posts if it matches current search
                if not self.search_var.get() or new_post.matches_search(self.search_var.get()):
                    self.filtered_posts.append(new_post)
                    self.filtered_indices.append(len(self.posts) - 1)
                
                # Update listbox
                self.refresh_post_list()
                
                # Save posts
                self.save_posts()
                
                # Clear editor
                self.text_area.delete("1.0", tk.END)
                self.category_var.set("")
                self.tags_var.set("")
                
                self.status_var.set(f"Created new post: {title}")
                messagebox.showinfo("Success", "Post created successfully!")
            else:
                messagebox.showwarning("Warning", "Content cannot be empty!")
        else:
            if title is not None:  # User pressed OK but didn't enter title
                messagebox.showwarning("Warning", "Title cannot be empty!")

    def on_post_select(self, event):
        """Handle post selection from listbox"""
        selection = self.post_listbox.curselection()
        if selection:
            index = selection[0]
            # Get the actual post index from filtered indices
            self.current_post_index = self.filtered_indices[index]
            post = self.posts[self.current_post_index]
            
            # Display post content in text area
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert("1.0", post.content)
            
            # Update category and tags
            self.category_var.set(post.category)
            self.tags_var.set(", ".join(post.tags))
            
            # Update word count
            self.update_word_count(None)
            
            self.status_var.set(f"Viewing post: {post.title}")

    def edit_post(self):
        """Edit the selected blog post"""
        if self.current_post_index is not None:
            content = self.text_area.get("1.0", tk.END).strip()
            if content:
                # Update the post
                post = self.posts[self.current_post_index]
                post.content = content
                post.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                post.category = self.category_var.get()
                tags_str = self.tags_var.get()
                post.tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
                
                # Update listbox entry
                # Find the position in filtered posts
                try:
                    filtered_index = self.filtered_indices.index(self.current_post_index)
                    self.post_listbox.delete(filtered_index)
                    self.post_listbox.insert(filtered_index, f"{post.title} ({post.timestamp})")
                except ValueError:
                    # Post not in filtered list, add it if it matches search
                    if not self.search_var.get() or post.matches_search(self.search_var.get()):
                        self.filtered_posts.append(post)
                        self.filtered_indices.append(self.current_post_index)
                        self.refresh_post_list()
                
                # Save posts
                self.save_posts()
                
                self.status_var.set(f"Edited post: {post.title}")
                messagebox.showinfo("Success", "Post updated successfully!")
            else:
                messagebox.showwarning("Warning", "Content cannot be empty!")
        else:
            messagebox.showwarning("Warning", "Select a post to edit!")

    def delete_post(self):
        """Delete the selected blog post"""
        if self.current_post_index is not None:
            # Confirm deletion
            post = self.posts[self.current_post_index]
            result = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{post.title}'?")
            
            if result:
                # Remove from posts list
                del self.posts[self.current_post_index]
                
                # Update filtered lists
                # Remove from filtered posts if present
                try:
                    filtered_index = self.filtered_indices.index(self.current_post_index)
                    del self.filtered_posts[filtered_index]
                    del self.filtered_indices[filtered_index]
                    
                    # Update indices in filtered_indices that are greater than current_post_index
                    self.filtered_indices = [i-1 if i > self.current_post_index else i for i in self.filtered_indices]
                except ValueError:
                    pass  # Not in filtered list
                
                # Remove from listbox
                self.refresh_post_list()
                
                # Save posts
                self.save_posts()
                
                # Clear editor
                self.text_area.delete("1.0", tk.END)
                self.category_var.set("")
                self.tags_var.set("")
                self.current_post_index = None
                
                self.status_var.set(f"Deleted post: {post.title}")
                messagebox.showinfo("Success", "Post deleted successfully!")
        else:
            messagebox.showwarning("Warning", "Select a post to delete!")

    def save_current_post(self):
        """Save the currently selected post"""
        if self.current_post_index is not None:
            self.edit_post()
        else:
            messagebox.showwarning("Warning", "Select a post to save!")

    def clear_editor(self):
        """Clear the text editor"""
        self.text_area.delete("1.0", tk.END)
        self.category_var.set("")
        self.tags_var.set("")
        self.current_post_index = None
        self.update_word_count(None)
        self.status_var.set("Editor cleared.")

    def preview_post(self):
        """Preview the current post in HTML format"""
        if self.current_post_index is not None:
            post = self.posts[self.current_post_index]
            title = post.title
            content = post.content
            category = post.category
            tags = post.tags
            timestamp = post.timestamp
            
            # Create HTML content for preview
            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title} - Preview</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #333; }}
        .meta {{ color: #666; font-size: 0.9em; }}
        .content {{ margin-top: 20px; line-height: 1.6; }}
        .category {{ background: #e0e0e0; padding: 2px 6px; border-radius: 3px; }}
        .tags {{ margin-top: 10px; }}
        .tag {{ background: #4CAF50; color: white; padding: 2px 6px; border-radius: 3px; margin-right: 5px; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="meta">
        <span>Published: {timestamp}</span>
        <span class="category">Category: {category}</span>
    </div>
    <div class="content">
        {self.format_text_for_html(content)}
    </div>
    <div class="tags">
        Tags: {' '.join(f'<span class="tag">{tag}</span>' for tag in tags)}
    </div>
</body>
</html>"""
            
            # Save to temporary file and open in browser
            temp_file = "temp_preview.html"
            try:
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                webbrowser.open(f'file://{os.path.abspath(temp_file)}')
                self.status_var.set("Preview opened in browser.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create preview: {str(e)}")
        else:
            messagebox.showwarning("Preview", "Select a post to preview!")

    def show_about(self):
        """Show about dialog"""
        about_text = """
Enhanced Personal Blog Application
Version 2.0

A feature-rich blog application with:
- Create, edit, and delete blog posts
- Persistent storage using JSON
- Timestamps for all posts
- Search functionality
- Categories and tags
- Text formatting (bold, italic, underline)
- Word count and statistics
- Export to HTML
- Backup and restore functionality
- Post preview
- User-friendly interface with menus and toolbars
        """
        messagebox.showinfo("About", about_text)


if __name__ == "__main__":
    root = tk.Tk()
    app = EnhancedBlogApp(root)
    root.mainloop()
