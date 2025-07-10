%% loadsGenerator_34nodes.m
%   [+] Autor: David Carrascal <david.carrascal@uah.es> 
%   [+] Fecha: 10 Jul 2025

clc;
close all;
clear variables;

%% Parámetros globales
PATH_LOADS_PROFILES = "";  % Ruta si fuese necesario

%% Carga de datos
generacion_file = fullfile(PATH_LOADS_PROFILES, "generacion.mat");
if exist(generacion_file, 'file')
    load(generacion_file);
    disp('generacion.mat cargado correctamente');
else
    error('generacion.mat no encontrado');
end

consumos_file = fullfile(PATH_LOADS_PROFILES, "consumos.mat");
if exist(consumos_file, 'file')
    load(consumos_file);
    disp('consumos.mat cargado correctamente');
else
    error('consumos.mat no encontrado');
end

%% Verificación de dimensiones
if size(perfiles_generacion, 2) ~= 96 || size(perfiles_consumo, 2) ~= 96
    error('Dimensión incorrecta en perfiles_generacion o perfiles_consumo. Deben tener 96 columnas.');
end

%% Reducción a 34 nodos
seed_d = 1998;
num_nodos = 34;
rng(seed_d); % Semilla para reproducibilidad

% Lista de nodos únicos
nodes = [800 802 806 808 810 812 814 816 818 820 822 824 826 828 830 832 834 836 838 840 842 844 846 848 850 852 854 856 858 860 862 864 888 890];

% Orden aleatorio de los nodos
random_nodes = nodes(randperm(length(nodes)));

total_nodos = size(perfiles_consumo, 1);

if total_nodos < num_nodos
    error('No hay suficientes perfiles para seleccionar 34 nodos.');
end

rng(seed_d); % Semilla para reproducibilidad
idx = randperm(total_nodos, num_nodos);
perfiles_generacion_sel = perfiles_generacion(idx, :);
perfiles_consumo_sel = perfiles_consumo(idx, :);
perfiles_balance = perfiles_generacion_sel - perfiles_consumo_sel;

%% Vector de tiempo para gráficas
time_vector = linspace(0, 24, 96);

%% Gráfico de balance total
gen_vector = sum(perfiles_generacion_sel, 1);
con_vector = sum(perfiles_consumo_sel, 1);
balance_vector = gen_vector - con_vector;

h = figure('Position', [100 100 800 700]);
subplot(3,1,1);
plot(time_vector, con_vector, 'r', 'LineWidth', 1.5);
title('Total Consumption (34 nodes)');
ylabel('Consumption (kW)');
xlim([0,24]); grid on;

subplot(3,1,2);
plot(time_vector, gen_vector, 'g', 'LineWidth', 1.5);
title('Total Generation (34 nodes)');
ylabel('Generation (kW)');
xlim([0,24]); grid on;

subplot(3,1,3);
hold on;
area(time_vector, balance_vector .* (balance_vector >= 0), 'FaceColor', 'green', 'EdgeColor', 'none');
area(time_vector, balance_vector .* (balance_vector < 0), 'FaceColor', 'red', 'EdgeColor', 'none');
plot(time_vector, balance_vector, 'k--', 'LineWidth', 1.5);
yline(0, 'k', 'LineWidth', 2);
title('Balance (Generation - Consumption)');
xlabel('Time (h)'); ylabel('kW');
xlim([0,24]); grid on;
hold off;

exportgraphics(h, "loads_balance_34nodes.pdf");
disp('Gráfica exportada: loads_balance_34nodes.pdf');

%% Exportar a CSV
output_file = 'loads_34nodes.csv';
num_intervals = 96;
time_intervals = 15:15:(num_intervals*15);
header = ['Bus_no', arrayfun(@num2str, time_intervals, 'UniformOutput', false)];

% Añadir Bus_no
bus_numbers = random_nodes.';
perfiles_with_bus = [bus_numbers perfiles_balance];

% Escribir cabecera
fileID = fopen(output_file, 'w');
fprintf(fileID, '%s\n', strjoin(header, ','));
fclose(fileID);

% Escribir datos
writematrix(perfiles_with_bus, output_file, 'WriteMode', 'append');

disp(['CSV generado: ', output_file]);
