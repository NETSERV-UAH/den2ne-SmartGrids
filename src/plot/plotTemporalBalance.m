%% plotTemporalBalance.m
%
%   [+] Autor: David Carrascal <david.carrascal@uah.es> 
%
%   [+] Fecha:  14 Feb 2025

function plotTemporalBalance(init, fin, result_path)
    
    % Intervalo de tiempo en minutos (cada delta representa 15 minutos)
    time_vector = datetime(2025, 2, 14, 0, 0, 0) + minutes(15 * (0:(fin-init)));
    
    % Número de criterios y balance de potencias (excluyendo distancia)
    num_criteria = 4;
    data_power = zeros(num_criteria, fin-init+1, 3); % 3 columnas para Ideal, Lossy, Lossy+Capacities
    
    % Leer los datos de los ficheros CSV
    for i = init:fin
        file_path = fullfile(result_path, strcat("csv/outdata_d", num2str(i), ".csv"));
        data_table = readtable(file_path, 'NumHeaderLines', 1);
        data = data_table{:,:};
        
        % Extraer los valores de balance de potencias para cada criterio (sin distancia)
        selected_criteria = [1, 3, 4, 5];
        data_power(:, i-init+1, :) = data(selected_criteria, [2 4 6]);
    end
    
    % Nombres de los criterios (sin distancia)
    criteria_labels = {'Hops', 'Losses', 'Power 0', 'Power 0 + Losses'};

    % Tipos de markers
    criteria_markers = {'-o', '-+', '-^', '-*'};
    
    % Títulos de las figuras
    case_titles = {"Ideal", "Lossy", "Lossy + Capacities"};
    
    for j = 1:3
        h = figure();
        set(gcf, 'Position', [100 100 900 700]);
        hold on;
        
        % Dibujar las curvas para cada criterio
        for c = 1:num_criteria
            plot(time_vector, data_power(c, :, j), criteria_markers{c}, 'LineWidth', 1.5, 'DisplayName', criteria_labels{c});
        end
        
        grid on;
        grid minor;
        xlabel('Time');
        ylabel('Power (kW)');
        title(["Power Balance - " case_titles{j}]);
        legend('Location', 'best');
        hold off;

        % Exportamos las cosas a lo nico style :)
        exportgraphics(h, fullfile(result_path, strcat('fig/powerBalance_', case_titles{j}, '.pdf')));
    end
end