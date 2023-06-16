from flask import Flask, render_template, request, redirect, make_response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import csv
import os
from io import StringIO
from pathlib import Path

db = SQLAlchemy()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///alphagrep.db'
db.init_app(app)

ALLOWED_EXTENSIONS = set(['csv'])

with app.app_context():
    db.drop_all()
    db.create_all()


class Student(db.Model):
    name = db.Column(db.String(100), primary_key=True, unique=True)
    password = db.Column(db.String(70), nullable=False)
    className = db.Column(db.String(100), nullable=False)
    scores = db.relationship("Score", backref = "student")

    def __repr__(self):
        return '<Student %r>' % self.name

class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True) 
    subject = db.Column(db.String(100), nullable=False)
    scoreDecimal = db.Column(db.Numeric(10,3), nullable=False)
    name = db.Column(db.String(100), db.ForeignKey('student.name'), nullable=False)
    # student = db.relationship("Student", backref="scores", foreign_keys=[name])

    def __repr__(self):
        return '<Score %r>' % self.id

@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'POST':
        studentName = request.form['name']
        studentPassword = request.form['password']
        studentClassName = request.form['className']
        new_student = Student(name = studentName, password = studentPassword, className = studentClassName)

        try:
            db.session.add(new_student)
            db.session.commit()
            # print("committed")
            return redirect('/')
        except:
            return render_template('error.html', error='An issue occured. There might be existing student with the same name')

    else:
        students = Student.query.order_by(Student.className).all()
        return render_template('index.html', students=students)

@app.route('/scores/<name>', methods=['POST', 'GET'])
def scores(name):
    # print(name)
    if request.method == 'POST':
        studentName = request.form['name']
        scoreSubject = request.form['subject']
        scoreDecimal = request.form['scoreDecimal']
        new_score = Score(name = studentName, subject = scoreSubject, scoreDecimal = scoreDecimal)

        try:
            db.session.add(new_score)
            db.session.commit()
            # print("committed score")
            return redirect('/scores/'+ name)
        except:
            return render_template('error.html', error='An issue occured. Unable to add new score.')

    else:
        student = Student.query.get_or_404(name)
        return render_template('score.html', scores=student.scores, name=name)


@app.route('/deleteStudent/<name>')
def deleteStudent(name):
    # print(name)
    student_to_delete = Student.query.get_or_404(name)

    try:
        #need to delete all scores that have dependencies 
        for score in student_to_delete.scores:
            db.session.delete(score)
        db.session.delete(student_to_delete)
        db.session.commit()
        return redirect('/')
    except:
        return render_template('error.html', error='An issue occured. There was a problem deleting the student')

@app.route('/deleteScore/<id>')
def deleteScore(id):
    # print(id)
    score_to_delete = Score.query.get_or_404(id)
    name = score_to_delete.name

    try:
        db.session.delete(score_to_delete)
        #check relationship here 
        db.session.commit()
        return redirect('/scores/'+ name)
    except:
        return render_template('error.html', error='An issue occured. There was a problem deleting the score')


@app.route('/updateStudent/<name>', methods=['GET', 'POST'])
def updateStudent(name):
    # print(name)
    student = Student.query.get_or_404(name)
    if request.method == 'POST':
        student.password = request.form['password']
        student.className = request.form['className']

        try:
            db.session.commit()
            return redirect('/')
        except:
            return render_template('error.html', error='An issue occured when updating student')
    else:
        return render_template('updateStudent.html', student=student)

@app.route('/updateScore/<id>', methods=['GET', 'POST'])
def updateScore(id):
    # print(id)
    score = Score.query.get_or_404(id)
    name = score.name
    if request.method == 'POST':
        score.subject = request.form['subject']
        score.scoreDecimal = request.form['scoreDecimal']

        try:
            db.session.commit()
            return redirect('/scores/'+ name)
        except:
            return render_template('error.html', error='An issue occured when updating score')
    else:
        return render_template('updateScore.html', score=score)

@app.route('/subject', methods=['GET'])
def subject():
    subjects = db.session.query(Score.subject).distinct().all()
    #print(subjects)
    top2 = []
    rank=[]
    for subject in subjects:
        scores = db.session.query(Score).filter(Score.subject==subject.subject).order_by(Score.scoreDecimal).all()
        if len(scores) > 1:
            top2.append(scores[1])
            rank.append(1)
        if len(scores) >0:
            top2.append(scores[0])
            rank.append(2)
    return render_template('subject.html', subjects=subjects, top2=top2, rank=rank)

@app.route('/scoresPerSubject/<subject>', methods=['GET'])
def scorePerSubject(subject):
    scores = db.session.query(Score).filter(Score.subject==subject).order_by(Score.scoreDecimal).all()
    # print(scores)
    return render_template('scoresPerSubject.html', scores=scores)

#ensure that format for file is csv
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#process uploaded csv file containing student info  
@app.route('/uploadStudent', methods=['GET', 'POST'])
def uploadStudent():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            new_filename = filename.split(".")[0] + '.csv'
            filepath = os.path.join('input', new_filename)
            file.save(filepath)
            try:
                with open(filepath) as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        # print(row)
                        new_student = Student(name = row['name'], password = row['password'], className = row['class'])
                        # print(new_student.password)
                        try:
                            db.session.add(new_student)
                            db.session.commit()
                        #    print("committed")
                        except:
                            return render_template('error.html', error='An issue occured. There might be existing student with the same name')
            except:
                return render_template('error.html', error='An issue occured. There might be a formatting error in the file provided ')
        return redirect('/')
    return render_template('index.html')

#process uploaded csv file containing scores info  
@app.route('/uploadScore', methods=['GET', 'POST'])
def uploadScore():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            new_filename = filename.split(".")[0] + '.csv'
            filepath = os.path.join('input', new_filename)
            file.save(filepath)
            with open(filepath) as file:
                reader = csv.DictReader(file)
                for row in reader:
                    student = db.session.query(Student).filter(Student.name==row['name'])
                    if(len(student.all())>0):
                        scoreDecimal = "0"
                        for i in row['score'].split():
                            if i.isdigit() or i=='.':
                                scoreDecimal += i
                        new_score = Score(name = row['name'], subject = row['subject'], scoreDecimal = float(scoreDecimal))
                        # print(new_score)
                        try:
                            db.session.add(new_score)
                            db.session.commit()
                            # print("committed")
                        except:
                            return render_template('error.html', error='An issue occured while uploading score')
            os.remove(filepath)
        return redirect('/subject')
    return render_template('index.html')

#download data as csv file 
@app.route('/downloadStudents')
def downloadStudents():
    header = ['Name', 'Password', 'Class']
    si = StringIO() #in-memory file-like object
    cw = csv.writer(si)
    cw.writerow(header)
    students = Student.query.order_by(Student.name).all()
    for student in students:
        cw.writerow([student.name, student.password, student.className])
    output = make_response(si.getvalue())
    i = 0
    downloads_path = str(Path.home() / "Downloads")
    name = "studentInformation.csv"
    while os.path.exists(downloads_path + "/" + name):
        i += 1
        name = "scoreInformation (" + str(i) + ").csv"
        # print(name)
    output.headers["Content-Disposition"] = "attachment; filename=" + name
    output.headers["Content-type"] = "csv"
    return output 

#download data as csv file 
@app.route('/downloadScores')
def downloadScoress():
    header = ['Name', 'Subject', 'Score']
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(header)
    scores = Score.query.order_by(Score.name).all()
    for score in scores:
        cw.writerow([score.name, score.subject, score.scoreDecimal])
    output = make_response(si.getvalue())
    i = 0
    downloads_path = str(Path.home() / "Downloads")
    name = "scoreInformation.csv"
    while os.path.exists(downloads_path + "/" + name):
        i += 1
        name = "scoreInformation (" + str(i) + ").csv"
        # print(name)
    output.headers["Content-Disposition"] = "attachment; filename=" + name
    output.headers["Content-type"] = "csv"
    return output 



if __name__ == "__main__":
    app.run(debug=True)



