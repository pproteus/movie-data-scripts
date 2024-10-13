options(warn = -1)
library(shiny)
library(bslib)
library(TeachingDemos)
options(warn = 0)

RATING_GRAPH_STRING = "Ratings"
COUNT_GRAPH_STRING = "Number of Users"
RATIO_GRAPH_STRING = "Ratios"

ui = page_sidebar(
	sidebar = sidebar(
		fileInput("filename", "Find a csv to graph:", accept=".csv"),
		radioButtons("graphtype", "Which type of graph?", 
			list(RATING_GRAPH_STRING, COUNT_GRAPH_STRING, RATIO_GRAPH_STRING)),
		checkboxInput("yeslabels", "Show labels"),
		sliderInput("size", "Size", min=0.5, max=3, value=1.8),
		sliderInput("xrange", "X Range", min=0, max=100, value=c(0, 100), round=1),
		sliderInput("yrange", "Y Range", min=0, max=100, value=c(0, 100), round=1),
		textInput("genrefilter", "Exclude Genres", value="Crime|Horror|Western|Documentary"),
		textInput("contentfilter", "Exclude Content", value="Intense violence|Abundant Swearing|Abundant Sexual Content")
		),
	plotOutput("plot", hover=hoverOpts(id="plot_hover", delayType = c("throttle")))
)

server = function(input, output){
	plot_info = reactiveValues()

	rating_graph_setup = function(){
		plot_info$xvar = "Letterboxd.Rating"
		plot_info$yvar = "IMDB.Rating"
		plot_info$xlab = "Letterboxd Rating"
		plot_info$ylab = "IMDB Rating"
		plot_info$log = ""
	}
	count_graph_setup = function(){
		plot_info$xvar = "Letterboxd.Count"
		plot_info$yvar = "IMDB.Count"
		plot_info$xlab = "Letterboxd Count"
		plot_info$ylab = "IMDB Count"
		plot_info$log = "xy"
	}
	ratio_graph_setup = function(){
		plot_info$xvar = "Count.Ratio"
		plot_info$yvar = "Rating.Ratio"
		plot_info$df[[plot_info$xvar]] = plot_info$df$Letterboxd.Count/plot_info$df$IMDB.Count
		plot_info$df[[plot_info$yvar]] = plot_info$df$Letterboxd.Rating/plot_info$df$IMDB.Rating
		plot_info$xlab = "IMDB Watched <--> Letterboxd Watched"
		plot_info$ylab = "IMDB Liked <--> Letterboxd Liked"
		plot_info$log = "x"
	}
	graph_setup = function(type){
		req(plot_info$df)
		if (type == RATING_GRAPH_STRING) rating_graph_setup()
		if (type == RATIO_GRAPH_STRING)  ratio_graph_setup()
		if (type == COUNT_GRAPH_STRING) count_graph_setup()
		req(plot_info$xvar)
		plot_info$x = plot_info$df[[plot_info$xvar]]
		plot_info$y = plot_info$df[[plot_info$yvar]]
		xrange = round(range(plot_info$x, na.rm=T), 1)
		yrange = round(range(plot_info$y, na.rm=T), 1)
		req(xrange)
		updateSliderInput(inputId="xrange", min=xrange[1], max=xrange[2], 
			value=xrange, step=diff(xrange)/100)
		updateSliderInput(inputId="yrange", min=yrange[1], max=yrange[2], 
			value=yrange, step=diff(yrange)/100)
	}

	apply_filters = function(){
		req(plot_info$df)
		if (input$contentfilter != ""){
			tryCatch(
				{plot_info$content_flag = grepl(input$contentfilter, plot_info$df$Objectionable.Content, ignore.case=T, perl=T) }
				, error = function(e) plot_info$content_flag = rep(F, length(plot_info$x))
				, warning = function(e) plot_info$content_flag = rep(F, length(plot_info$x))
			)
		}
		else {
			plot_info$content_flag = rep(F, length(plot_info$x))
		}
		if (input$genrefilter != ""){
			tryCatch(
				{plot_info$genre_flag = grepl(input$genrefilter, plot_info$df$Genres, ignore.case=T, perl=T) }
				, error = function(e) plot_info$genre_flag = rep(F, length(plot_info$x))
				, warning = function(e) plot_info$genre_flag = rep(F, length(plot_info$x))
			)
		}
		else {
			plot_info$genre_flag = rep(F, length(plot_info$x))
		}
		plot_info$filter_flag = plot_info$content_flag | plot_info$genre_flag
	}

	observeEvent(input$filename, {
		df = read.csv(input$filename$datapath, sep="\t")
		plot_info$df = df
		plot_info$df[["Letterboxd.Rating"]] = jitter(plot_info$df[["Letterboxd.Rating"]])
		plot_info$df[["IMDB.Rating"]] = jitter(plot_info$df[["IMDB.Rating"]])
		apply_filters()
		plot_info$highlight_flag = rep(F, length(plot_info$x))
		graph_setup(input$graphtype)
		plot_info$labels = paste(plot_info$df$Title, " (", plot_info$df$Year, ")", sep="")
	})

	observeEvent(input$graphtype, {
		graph_setup(input$graphtype)
	})

	observeEvent(input$contentfilter, {
		apply_filters()
	})

	observeEvent(input$genrefilter, {
		apply_filters()
	})

	observeEvent(input$plot_hover, {
		req(plot_info$df)
		plot_info$highlight_flag = nearPoints(plot_info$df, 
			input$plot_hover, allRows=T, 
			xvar=plot_info$xvar, yvar=plot_info$yvar,
			threshold=500, maxpoints=1)$selected_
	})

	output$plot = renderPlot({
		req(plot_info$x, plot_info$y)
		plot(plot_info$y~plot_info$x, pch=19, cex=input$size, cex.lab=sqrt(input$size), 
				xlab=plot_info$xlab, ylab=plot_info$ylab, log=plot_info$log, 
				xlim=input$xrange, ylim=input$yrange, col=ifelse(plot_info$filter_flag, "grey", "black"))

		if (input$graphtype == RATING_GRAPH_STRING){
			abline(0,2, lty=2)
			fit = lm(y~x+I(x^2), data=data.frame(x=plot_info$x, y=plot_info$y))
			xseq = seq(0,5,0.01)
			p = predict(fit, newdata=data.frame(x=xseq))
			lines(xseq,p)
		}
		if (input$graphtype == COUNT_GRAPH_STRING){
			abline(0,1, lty=2)
		}
		if (input$graphtype == RATIO_GRAPH_STRING){
			abline(h=0.5, lty=2)
			abline(v=1, lty=2)
		}
		if (input$yeslabels) {
			text(plot_info$x, plot_info$y, offset=0.5, pos=3, plot_info$labels, cex=0.7*input$size, col="grey")
			if (! all(plot_info$filter_flag)) {
				text(plot_info$x[which(!plot_info$filter_flag)], plot_info$y[which(!plot_info$filter_flag)], 
					offset=0.5, pos=3, plot_info$labels[which(!plot_info$filter_flag)], cex=0.7*input$size, col="black")
			}
		}
		flag=plot_info$highlight_flag
		if(sum(flag) & input$yeslabels)	{		
			points(plot_info$y[flag]~plot_info$x[flag], pch=19, cex=input$size, col="blue")
			TeachingDemos::shadowtext(plot_info$x[flag], plot_info$y[flag], offset=0.5, pos=3, 
				plot_info$labels[flag], cex=0.7*input$size, col="white", bg="black", r=0.2)
		}
		
	})	
}

shinyApp(ui=ui, server=server)


##TODO
# - fleeting image on plot load. Caused by the sliders?
# - how to differentiate two points that are right on top of each other?