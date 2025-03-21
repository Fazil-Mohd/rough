Overloading happens when you have multiple methods with the same name but different parameters (either in type or number).
in this "area" is the method overloading
	
package MODULE2;
import java.util.Scanner;
class OverLoadDemo {
	void area(float x) {
		System.out.println("The area of the square is "+Math.pow(x, 2)+" sq units");
	}
	void area(float x, float y) {
		System.out.println("The area of the rectangle is "+x*y+" sq units");
	}
	void area(double x) {
		double z = 3.14 * x * x;
		System.out.println("The area of the cirecl is "+z+" sq units");
	}
}
class OverLoad {
	public static void main (String args[]) {
		Scanner sc = new Scanner(System.in);
		OverLoadDemo ob = new OverLoadDemo();
		System.out.println("Enter side Length of Square:");
		float squareSide = sc.nextFloat();
        ob.area(squareSide);
		System.out.println("Enter length of rectangle:");
		float rectLength = sc.nextFloat();
		System.out.print("Enter width of rectangle: ");
        float rectWidth = sc.nextFloat();
        ob.area(rectLength, rectWidth);
		System.out.println("Enter radius of circle: ");
		double circleRadius = sc.nextDouble();
        ob.area(circleRadius);
	}
}
