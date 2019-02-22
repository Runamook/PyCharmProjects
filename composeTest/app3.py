from composeTest.App.app2 import myapp

db_name = "/home/egk/PycharmProjects/composeTest/app/test.db"
app = myapp(__name__, db_name)
app.run()
