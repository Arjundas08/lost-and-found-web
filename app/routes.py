# /lost_and_found_app/app/routes.py
from flask import render_template, request, redirect, url_for, flash, Blueprint, current_app, abort
from flask_login import login_user, current_user, logout_user, login_required
from werkzeug.utils import secure_filename
from . import db
from .models import User, Item
from .forms import LoginForm, RegistrationForm, ItemForm
import os
import uuid

main_bp = Blueprint('main', __name__) # <-- THIS IS THE MISSING OR INCORRECT LINE

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def save_picture(form_picture):
    random_hex = uuid.uuid4().hex
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.config['UPLOAD_FOLDER'], picture_fn)
    form_picture.save(picture_path)
    return picture_fn

def delete_picture(filename):
    if filename:
        picture_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(picture_path):
            os.remove(picture_path)

@main_bp.route("/")
def welcome():
    return render_template("welcome.html")

@main_bp.route("/dashboard")
def dashboard():
    q = request.args.get("q", "").strip()
    filter_status = request.args.get("status", "").strip()
    filter_claim = request.args.get("claim", "").strip()

    query = Item.query
    if q:
        search_term = f"%{q}%"
        query = query.filter(
            (Item.name.ilike(search_term)) | (Item.description.ilike(search_term))
        )
    if filter_status in ("Lost", "Found"):
        query = query.filter_by(status=filter_status)
    if filter_claim == "claimed":
        query = query.filter_by(claimed=True)
    elif filter_claim == "unclaimed":
        query = query.filter_by(claimed=False)

    items = query.order_by(Item.date_posted.desc()).all()
    return render_template("dashboard.html", items=items, q=q,
                           filter_status=filter_status, filter_claim=filter_claim)

@main_bp.route("/item/<int:item_id>")
def item_detail(item_id: int):
    item = Item.query.get_or_404(item_id)
    return render_template("item_detail.html", item=item)

@main_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_item():
    form = ItemForm()
    if form.validate_on_submit():
        filename = None
        if form.image.data:
            if allowed_file(form.image.data.filename):
                filename = save_picture(form.image.data)
            else:
                flash("Invalid image file type. Allowed types are png, jpg, jpeg, gif.", "danger")
                return render_template("add_edit_item.html", title="Add New Item", form=form)

        item = Item(name=form.name.data, description=form.description.data,
                    status=form.status.data, image=filename, owner=current_user)
        db.session.add(item)
        db.session.commit()
        flash("Item added successfully!", "success")
        return redirect(url_for("main.dashboard"))
    return render_template("add_edit_item.html", title="Add New Item", form=form)

@main_bp.route("/edit/<int:item_id>", methods=["GET", "POST"])
@login_required
def edit_item(item_id: int):
    item = Item.query.get_or_404(item_id)
    if item.owner != current_user:
        abort(403) # Forbidden

    form = ItemForm()
    if form.validate_on_submit():
        item.name = form.name.data
        item.description = form.description.data
        item.status = form.status.data

        if form.image.data:
            if allowed_file(form.image.data.filename):
                delete_picture(item.image) # Delete old picture
                item.image = save_picture(form.image.data)
            else:
                flash("Invalid image file type.", "danger")
                return render_template("add_edit_item.html", title="Edit Item", form=form, item=item)

        db.session.commit()
        flash("Item updated successfully!", "info")
        return redirect(url_for("main.item_detail", item_id=item.id))

    elif request.method == 'GET':
        form.name.data = item.name
        form.description.data = item.description
        form.status.data = item.status

    return render_template("add_edit_item.html", title="Edit Item", form=form, item=item)

@main_bp.route("/delete/<int:item_id>", methods=["POST"])
@login_required
def delete_item(item_id: int):
    item = Item.query.get_or_404(item_id)
    if item.owner != current_user:
        abort(403)
    delete_picture(item.image) # Delete image file
    db.session.delete(item)
    db.session.commit()
    flash("Item has been deleted.", "danger")
    return redirect(url_for("main.dashboard"))

@main_bp.route("/claim/<int:item_id>")
@login_required
def claim_item(item_id: int):
    item = Item.query.get_or_404(item_id)
    if item.owner != current_user:
        abort(403)
    item.claimed = True
    db.session.commit()
    flash("Marked as claimed.", "warning")
    return redirect(url_for("main.dashboard"))

@main_bp.route("/unclaim/<int:item_id>")
@login_required
def unclaim_item(item_id: int):
    item = Item.query.get_or_404(item_id)
    if item.owner != current_user:
        abort(403)
    item.claimed = False
    db.session.commit()
    flash("Marked as unclaimed.", "secondary")
    return redirect(url_for("main.dashboard"))

# --- Auth Routes ---

@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in.', 'success')
        return redirect(url_for('main.login'))
    return render_template('auth/register.html', title='Register', form=form)

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        else:
            flash('Login Unsuccessful. Please check email and password.', 'danger')
    return render_template('auth/login.html', title='Login', form=form)

@main_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.welcome'))

# --- Error Handlers ---
@main_bp.app_errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@main_bp.app_errorhandler(403)
def forbidden_error(error):
    flash('You do not have permission to access this page.', 'danger')
    return redirect(url_for('main.dashboard'))