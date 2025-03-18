%% Main
clc
close all
clear variables

% First we have to indicate where are the loads distribution
PATH_LOADS_DIST = "";

% Lets read the csv with all the info
data_table = readtable(strcat(PATH_LOADS_DIST, "loads_v2.csv"), 'NumHeaderLines', 1);

% Parse from table to matrix 
data = data_table{:, 2:end};

% Flatten the matrix to a single vector
data_vector = data(:);

% Plot histogram
h = figure();
histogram(data_vector,50);
grid on;
title('Distribution of end node load profiles');
xlabel('Power (kW)');
ylabel('Frecuency');
exportgraphics(h,"fig_pdf_loads.pdf")
