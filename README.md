This repo contains the backend code for my serverless resume website

cloudformation/ - contains the Cloudformation template that sets up all required AWS infrastructure

genJSONCode/ - contains a simple python script to format a .py file into JSON for use with Cloudformation

lambdaFunctions/ - contains all of the lambda functions that are included in the Cloudformation template as .py files

lambdaLayers/ - contains a lambda layer for pillow, the PIL fork for python 3, this is required to draw the challenges in resumeGenerateChallengeLambda.py as it is not built in to lambda

.github/workflows/ - contains the GitHub Actions workflow files to update the stack and the pillow.zip file

[Front-end repository](https://github.com/mattisz/resume-frontend)

[See my resume](https://resume.mattisz.com)

[See the full write up](https://resume.mattisz.com/about.html)