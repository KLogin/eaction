import cv2
import sys

def on_mouse(event, x, y, flags, params):
    global img, start_point
    if event == cv2.EVENT_LBUTTONDOWN:
        print('Start Mouse Position: '+str(x)+', '+str(y))
        # print(y , width/2)
        if(x < (width/2)):
            cv2.putText(img, "point("+str(x)+","+str(y)+")", (x+10, y+10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        else:
            cv2.putText(img, "point("+str(x)+","+str(y)+")", (x-190, y+10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.circle(img, (x, y), 5, (0, 0, 255), -1)
        start_point = (x, y)

    elif event == cv2.EVENT_LBUTTONUP:
        print('End Mouse Position: '+str(x)+', '+str(y))
        cv2.line(img, start_point, (x, y), (255, 255, 0), 3)
        if(x < (width/2)):
            cv2.putText(img, "point("+str(x)+","+str(y)+")", (x+10, y+10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        else:
            cv2.putText(img, "point("+str(x)+","+str(y)+")", (x-190, y+10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        start_point = None
        cv2.circle(img, (x, y), 5, (0, 0, 255), -1)

if __name__ == '__main__':
    if(len(sys.argv) < 2):
        print("Please add a video file, for example: python "+sys.argv[0]+" video.mp4")
    else:
        print("Try open video file: ", sys.argv[1])
        cap = cv2.VideoCapture(sys.argv[1])
        if (cap.isOpened() == False):
            print("Error opening video file")
        else:
            ret, img = cap.read()
            if ret == True:
                cv2.namedWindow('real image')
                cv2.setMouseCallback('real image', on_mouse, 0)
                is_first = False
                start_point = None
                height, width, channels = img.shape
                print(height, width)
                while(1):
                    cv2.imshow('real image', img)
                    if cv2.waitKey(20) & 0xFF == ord('q'):
                        cap.release()
                        # Closes all the frames
                        cv2.destroyAllWindows()
                        break