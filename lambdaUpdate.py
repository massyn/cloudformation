import argparse
from zipfile import ZipFile
import boto3
import io
import json
import os

def main():
    parser = argparse.ArgumentParser(description='Update Lambda function')
    parser.add_argument('-fn', help='Function name', required=True)
    parser.add_argument('-files',help='List of files to combine into a package',nargs='+', required=True)
    parser.add_argument('-s3',help='The S3 bucket to be used as staging (for larger lambda functions)')
    args = parser.parse_args()

    obj = io.BytesIO()
    with ZipFile(obj, 'w') as zip_object:
        row = 0
        for f in args.files:
            if os.path.isdir(f):
                print(f"{f} is a folder")
                for r, d, F in os.walk(f):
                    for file in F:
                        x = os.path.join(r, file)[len(f)+1:]
                        print(f" - Zipping -- {f}/{x}")
                        zip_object.write(f"{f}/{x}",x)
                        #print(x)
            else:
                # Adding files that need to be zipped
                print(f" - Zipping -- {f}")
                if row == 0:
                    filename = 'index.py'
                else:
                    filename = f
                
                zip_object.write(f,filename)
                row += 1
    
    # -- update the lambda function's code
    if not args.s3:
        response = boto3.client('lambda').update_function_code(
            FunctionName=args.fn,
            ZipFile=obj.getvalue(),
            Publish=True
        )
        print(json.dumps(response,indent=4))
    else:
        print("Uploading to S3...")
        S3Key = "f{args.fn}.zip"
        obj.seek(0)
        s3 = boto3.resource('s3').Bucket(args.s3).upload_fileobj(obj, S3Key)
        response = boto3.client('lambda').update_function_code(
            FunctionName=args.fn,
            S3Bucket=args.s3,
            S3Key=S3Key,
            Publish=True
        )
        print(json.dumps(response,indent=4))

if __name__ == '__main__':
    main()



