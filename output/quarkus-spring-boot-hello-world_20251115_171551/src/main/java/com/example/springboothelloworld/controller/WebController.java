package com.example.springboothelloworld.controller;

import jakarta.ws.rs.GET;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.QueryParam;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;

@Path("/web")
public class WebController {

    @GET
    @Path("/message")
    @Produces(MediaType.TEXT_PLAIN)
    public String webMessage(@QueryParam("name") String name) {
        return "Hello, " + name;
    }
}