options(warn = -1)
library(shiny)
library(bslib)
options(warn = 0)

make_graph = function(filename, type=1, text=False, size=1) {
	if (is.null(filename)) return(NULL)
	x = read.csv(filename, sep="\t")
	Letterboxd = x$Letterboxd.Rating
	IMDB = x$IMDB.Rating
	
	if (type==1){ ### rating, by site
	plot(IMDB~Letterboxd, pch=19, cex=size, cex.lab=sqrt(size))
	abline(0,2, lty=2)
	fit = lm(IMDB~Letterboxd+I(Letterboxd^2))
	xseq = seq(0,5,0.01)
	p = predict(fit, newdata=data.frame(Letterboxd=xseq))
	lines(xseq,p)
	if (text) text(x$Letterboxd.Rating, x$IMDB.Rating+(max(IMDB, na.rm=T)-min(IMDB, na.rm=T))/50, x$Title, cex=0.7*size)
	}
	if (type==2){## ratio vs ratio
	Rating = x$Letterboxd.Rating/x$IMDB.Rating
	Count = x$Letterboxd.Count/x$IMDB.Count
	plot(Rating~Count, pch=19, cex=size, cex.lab=sqrt(size), log="x", xlab="IMDB Watched <--> Letterboxd Watched", ylab="IMDB Liked <--> Letterboxd Liked")
	abline(0.5, 0, lty=2)
	if (text) text(Count, Rating +(max(Rating, na.rm=T)-min(Rating, na.rm=T))/50, x$Title, cex=size)
	}
}

ui = page_sidebar(
	sidebar = sidebar(
		fileInput("filename", "Find a csv to graph:", accept=".csv"),
		radioButtons("graphtype", "Which type of graph?", list(1,2)),
		checkboxInput("yeslabels", "Label points?"),
		sliderInput("size", "Size", value=1.8, min=0.1, max=10)
		),
	plotOutput("plot")
)

server = function(input, output){
	filename = "mcu.csv"
	output$plot = renderPlot(make_graph(
		input$filename$datapath, type=input$graphtype,
		text=input$yeslabels, size=input$size))	
}

shinyApp(ui=ui, server=server)
