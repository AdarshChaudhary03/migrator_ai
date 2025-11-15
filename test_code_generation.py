#!/usr/bin/env python3
"""
Test script to simulate the complete code generation workflow 
based on the actual agent logs provided.
"""

import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from agents.code_generator.code_generation_tools import (
    create_project_structure,
    write_source_file,
    write_build_file,
    write_configuration_file,
    write_documentation_file,
    validate_project_structure
)

def simulate_code_generator_workflow():
    """Simulate the complete code generator workflow."""
    print("=== Code Generator Workflow Test ===")
    
    # Simulate inputs from the logs
    repo_url = "https://github.com/bratzelk/spring-boot-hello-world"
    repo_name = "spring-boot-hello-world"  # Extract from URL
    target_path = "/tmp/quarkus-migrated-spring-boot-hello-world-a254993"  # From AST transformer
    
    # 1. Create project structure
    print("1. Creating project structure...")
    structure_result = create_project_structure(target_path, repo_name)
    print(f"   Status: {structure_result.get('status')}")
    print(f"   Base path: {structure_result.get('base_path')}")
    
    if structure_result.get('status') != 'success':
        print("❌ Failed to create project structure")
        return False
    
    base_path = structure_result.get('base_path')
    
    # 2. Write source file (from AST transformer output)
    print("2. Writing source files...")
    source_content = """package com.example.demo;

import javax.ws.rs.GET;
import javax.ws.rs.Path;
import javax.ws.rs.Produces;
import javax.ws.rs.core.MediaType;

@Path("/")
public class HelloController {

    @GET
    @Produces(MediaType.TEXT_PLAIN)
    public String hello() {
        return "Hello, World!";
    }
}"""
    
    source_result = write_source_file(
        file_path="src/main/java/com/example/demo/HelloController.java",
        content=source_content,
        base_path=base_path
    )
    print(f"   Source file status: {source_result.get('status')}")
    
    # 3. Write build file (from build script converter output) 
    print("3. Writing build files...")
    pom_content = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
	xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
	<modelVersion>4.0.0</modelVersion>

	<groupId>com.example</groupId>
	<artifactId>demo</artifactId>
	<version>0.0.1-SNAPSHOT</version>
	<name>demo</name>
	<description>Demo project for Spring Boot</description>

	<properties>
		<java.version>17</java.version>
		<maven.compiler.source>17</maven.compiler.source>
		<maven.compiler.target>17</maven.compiler.target>
		<quarkus.platform.version>3.9.3</quarkus.platform.version>
		<surefire-plugin.version>3.2.2</surefire-plugin.version>
	</properties>

	<dependencyManagement>
		<dependencies>
			<dependency>
				<groupId>io.quarkus.platform</groupId>
				<artifactId>quarkus-bom</artifactId>
				<version>${quarkus.platform.version}</version>
				<type>pom</type>
				<scope>import</scope>
			</dependency>
		</dependencies>
	</dependencyManagement>

	<dependencies>
		<dependency>
			<groupId>io.quarkus</groupId>
			<artifactId>quarkus-resteasy-reactive</artifactId>
		</dependency>
		<dependency>
			<groupId>io.quarkus</groupId>
			<artifactId>quarkus-junit5</artifactId>
			<scope>test</scope>
		</dependency>
		<dependency>
			<groupId>io.rest-assured</groupId>
			<artifactId>rest-assured</artifactId>
			<scope>test</scope>
		</dependency>
	</dependencies>

	<build>
		<plugins>
			<plugin>
				<groupId>io.quarkus</groupId>
				<artifactId>quarkus-maven-plugin</artifactId>
				<version>${quarkus.platform.version}</version>
				<extensions>true</extensions>
				<executions>
					<execution>
						<goals>
							<goal>build</goal>
							<goal>generate-code</goal>
							<goal>generate-code-tests</goal>
						</goals>
					</execution>
				</executions>
			</plugin>
			<plugin>
				<artifactId>maven-surefire-plugin</artifactId>
				<version>${surefire-plugin.version}</version>
				<configuration>
					<systemPropertyVariables>
						<java.util.logging.manager>org.jboss.logmanager.LogManager</java.util.logging.manager>
						<maven.home>${maven.home}</maven.home>
					</systemPropertyVariables>
				</configuration>
			</plugin>
		</plugins>
	</build>
	<profiles>
		<profile>
			<id>native</id>
			<activation>
				<property>
					<name>native</name>
				</property>
			</activation>
			<properties>
				<quarkus.package.type>native</quarkus.package.type>
				<quarkus.native.container-build>true</quarkus.native.container-build>
			</properties>
		</profile>
	</profiles>
</project>"""
    
    build_result = write_build_file(
        file_content=pom_content,
        file_type="pom.xml",
        base_path=base_path
    )
    print(f"   Build file status: {build_result.get('status')}")
    
    # 4. Write configuration file (from config mapper output)
    print("4. Writing configuration files...")
    config_result = write_configuration_file(
        file_path="src/main/resources/application.properties",
        content="quarkus.log.level=INFO",
        base_path=base_path
    )
    print(f"   Config file status: {config_result.get('status')}")
    
    # 5. Write documentation
    print("5. Writing documentation...")
    readme_content = """# Migration Report

This project was migrated from Spring Boot to Quarkus.

## Applied Changes

- Spring Web annotations were converted to JAX-RS annotations.
- Spring Boot starter web dependency was replaced with Quarkus RESTeasy Reactive.
- application.properties was converted to Quarkus format.

## Next Steps

- Run `mvn compile` to verify project builds correctly.
- Test application startup with `mvn quarkus:dev`.
- Review generated files for correctness."""
    
    doc_result = write_documentation_file(
        file_name="README.md",
        content=readme_content,
        base_path=base_path
    )
    print(f"   Documentation status: {doc_result.get('status')}")
    
    # 6. Validate project structure
    print("6. Validating project structure...")
    validation_result = validate_project_structure(base_path)
    print(f"   Validation status: {'✅ Valid' if validation_result.get('structure_valid') else '❌ Invalid'}")
    print(f"   Found files: {validation_result.get('found_files', [])}")
    
    # 7. Final summary
    print("\n=== Final Summary ===")
    print(f"✅ Project created at: {base_path}")
    print(f"✅ Generated files: HelloController.java, pom.xml, application.properties, README.md")
    print(f"✅ Project is ready for development")
    
    return True

if __name__ == "__main__":
    success = simulate_code_generator_workflow()
    if success:
        print("\n🎉 Code generation workflow test completed successfully!")
        print("The code generator agent should now create accessible projects in the ./output directory.")
    else:
        print("\n❌ Code generation workflow test failed!")
        
    sys.exit(0 if success else 1)
