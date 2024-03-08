from server import app, db

if __name__ == '__main__':
    response = input('Are you sure you want to delete and recreate the database? y/n ')
    if response != 'y':
        print('Aborting...')
        exit()

    with app.app_context():
        db.drop_all()
        db.create_all()
        print('Database initialized.')
