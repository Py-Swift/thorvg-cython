

# Testing Python on iOS

The iOS/testbed folder that contains an Xcode project that is able to run the iOS test suite. This project converts the Python test suite into a single test case in Xcode's XCTest framework. The single XCTest passes if the test suite passes.

To run the test suite, configure a Python build for an iOS simulator (i.e., --host=arm64-apple-ios-simulator or --host=x86_64-apple-ios-simulator ), specifying a framework build (i.e. --enable-framework). Ensure that your PATH has been configured to include the iOS/Resources/bin folder and exclude any non-iOS tools, then run:

$ make all
$ make install
$ make testios
This will:

Build an iOS framework for your chosen architecture;
Finalize the single-platform framework;
Make a clean copy of the testbed project;
Install the Python iOS framework into the copy of the testbed project; and
Run the test suite on an "iPhone SE (3rd generation)" simulator.
On success, the test suite will exit and report successful completion of the test suite. On a 2022 M1 MacBook Pro, the test suite takes approximately 15 minutes to run; a couple of extra minutes is required to compile the testbed project, and then boot and prepare the iOS simulator.

Debugging test failures

Running make testios generates a standalone version of the iOS/testbed project, and runs the full test suite. It does this using iOS/testbed itself - the folder is an executable module that can be used to create and run a clone of the testbed project.

You can generate your own standalone testbed instance by running:

$ python iOS/testbed clone --framework iOS/Frameworks/arm64-iphonesimulator my-testbed
This invocation assumes that iOS/Frameworks/arm64-iphonesimulator is the path to the iOS simulator framework for your platform (ARM64 in this case); my-testbed is the name of the folder for the new testbed clone.

You can then use the my-testbed folder to run the Python test suite, passing in any command line arguments you may require. For example, if you're trying to diagnose a failure in the os module, you might run:

$ python my-testbed run -- test -W test_os
This is the equivalent of running python -m test -W test_os on a desktop Python build. Any arguments after the -- will be passed to testbed as if they were arguments to python -m on a desktop machine.